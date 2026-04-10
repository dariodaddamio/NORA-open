import asyncio
import os
import re
import time
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv

from process_link import (
    LowTranscriptSignalError,
    estimate_processing_for_url,
    get_run_eta_snapshot,
    get_processed_urls,
    process_instagram_link,
    process_instagram_link_detailed,
)


load_dotenv()

TOKEN = os.environ["DISCORD_TOKEN"]
INSTAGRAM_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/[^\s>]+", re.IGNORECASE)

SAVEALL_DEFAULT_MAX_MESSAGES = int(os.getenv("SAVEALL_DEFAULT_MAX_MESSAGES", "500"))
SAVEALL_DEFAULT_MAX_NEW_LINKS = int(os.getenv("SAVEALL_DEFAULT_MAX_NEW_LINKS", "50"))
SAVEALL_HARD_MAX_MESSAGES = int(os.getenv("SAVEALL_HARD_MAX_MESSAGES", "5000"))
SAVEALL_HARD_MAX_NEW_LINKS = int(os.getenv("SAVEALL_HARD_MAX_NEW_LINKS", "200"))
SAVEALL_PROGRESS_EVERY = int(os.getenv("SAVEALL_PROGRESS_EVERY", "10"))
DISCORD_ETA_UPDATE_INTERVAL_SECONDS = max(3, int(os.getenv("DISCORD_ETA_UPDATE_INTERVAL_SECONDS", "10")))


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

_synced = False
_guild_locks: dict[int, asyncio.Lock] = {}
_force_run_locks: dict[tuple[int, str], asyncio.Lock] = {}


def _truncate_err(err: Exception) -> str:
    msg = str(err)
    if len(msg) > 1800:
        return msg[:1800] + "…"
    return msg


def _extract_instagram_urls(text: str) -> list[str]:
    if not text:
        return []
    return [m.group(0).strip() for m in INSTAGRAM_URL_RE.finditer(text)]


def _format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}h {mins}m {secs}s"
    if mins:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def _guild_lock(guild_id: int) -> asyncio.Lock:
    lock = _guild_locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _guild_locks[guild_id] = lock
    return lock


def _force_lock(guild_id: int, url: str) -> asyncio.Lock:
    key = (guild_id, url.strip())
    lock = _force_run_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _force_run_locks[key] = lock
    return lock


class TryAnywayView(discord.ui.View):
    def __init__(self, *, url: str, requester_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.url = url
        self.requester_id = requester_id
        self.guild_id = guild_id

    @discord.ui.button(label="Try anyway", style=discord.ButtonStyle.primary)
    async def try_anyway(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore[override]
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("Only the original requester can use this button.", ephemeral=True)
            return
        lock = _force_lock(self.guild_id, self.url)
        if lock.locked():
            await interaction.response.send_message("A forced run is already in progress for this link.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        async with lock:
            try:
                note_path = await asyncio.to_thread(process_instagram_link, self.url, force_process=True)
                await interaction.followup.send(f"Forced processing complete. Saved note: `{note_path}`")
                # Remove the button from the post-click response thread while
                # keeping the original gate message unchanged.
                await interaction.edit_original_response(view=None)
            except Exception as e:
                await interaction.followup.send(f"Forced processing failed: `{_truncate_err(e)}`")


@client.event
async def on_ready():
    global _synced
    print(f"Logged in as {client.user}")
    if not _synced:
        await tree.sync()
        _synced = True
        print("Slash commands synced.")


@tree.command(name="save", description="Process one Instagram URL into an Obsidian note.")
@app_commands.describe(url="Instagram URL (reel/post) to process")
async def save(interaction: discord.Interaction, url: str):
    if not INSTAGRAM_URL_RE.search(url or ""):
        await interaction.response.send_message(
            "That does not look like a valid Instagram URL.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    clean_url = url.strip()
    started = time.monotonic()
    estimate_data = await asyncio.to_thread(estimate_processing_for_url, clean_url)
    estimated_total = float(estimate_data.get("estimated_total_seconds", 0.0) or 0.0)
    video_duration = float(estimate_data.get("video_duration_seconds", 0.0) or 0.0)
    estimate_confidence = str(estimate_data.get("confidence", "conservative"))
    sample_counts = estimate_data.get("sample_counts", {}) or {}
    known_samples = [int(v) for v in sample_counts.values() if isinstance(v, (int, float))]
    min_samples = min(known_samples) if known_samples else 0
    status_message = await interaction.followup.send(
        "🧠 NORA is thinking...\n"
        f"🎬 Video length: `{_format_duration(video_duration)}`\n"
        f"⏱️ Estimated completion: `~{_format_duration(estimated_total)}`\n"
        f"📊 ETA mode: `{estimate_confidence}` (samples: {min_samples})",
        wait=True,
    )

    stop_updater = asyncio.Event()

    async def _eta_updater() -> None:
        while not stop_updater.is_set():
            await asyncio.sleep(DISCORD_ETA_UPDATE_INTERVAL_SECONDS)
            if stop_updater.is_set():
                break
            elapsed = time.monotonic() - started
            snap = get_run_eta_snapshot(clean_url)
            if snap:
                remaining = max(0.0, float(snap.get("estimated_remaining_seconds", 0.0) or 0.0))
                elapsed_runtime = float(snap.get("elapsed_seconds", elapsed) or elapsed)
                snap_confidence = str(snap.get("confidence", estimate_confidence))
                snap_samples = snap.get("sample_counts", sample_counts) or {}
                snap_known_samples = [int(v) for v in snap_samples.values() if isinstance(v, (int, float))]
                snap_min_samples = min(snap_known_samples) if snap_known_samples else min_samples
            else:
                remaining = max(0.0, estimated_total - elapsed)
                elapsed_runtime = elapsed
                snap_confidence = estimate_confidence
                snap_min_samples = min_samples
            try:
                await status_message.edit(
                    content=(
                        "🧠 NORA is thinking...\n"
                        f"🎬 Video length: `{_format_duration(video_duration)}`\n"
                        f"⏱️ ETA remaining: `~{_format_duration(remaining)}`\n"
                        f"⌛ Elapsed: `{_format_duration(elapsed_runtime)}`\n"
                        f"📊 ETA mode: `{snap_confidence}` (samples: {snap_min_samples})"
                    )
                )
            except Exception:
                return

    updater_task = asyncio.create_task(_eta_updater())

    try:
        result = await asyncio.to_thread(process_instagram_link_detailed, clean_url)
        stop_updater.set()
        await updater_task
        await status_message.edit(
            content=(
                "✅ NORA finished processing.\n"
                f"🎬 Video length: `{_format_duration(result.video_duration_seconds)}`\n"
                f"⏱️ Total runtime: `{_format_duration(result.elapsed_seconds)}`"
            )
        )
        await interaction.followup.send(
            f"Saved note: `{result.note_path}`\n"
            f"Runtime: `{_format_duration(result.elapsed_seconds)}` "
            f"(video: `{_format_duration(result.video_duration_seconds)}`)"
        )
    except LowTranscriptSignalError as e:
        stop_updater.set()
        await updater_task
        elapsed = time.monotonic() - started
        await status_message.edit(
            content=(
                "⚠️ NORA paused due to transcript quality gate.\n"
                f"🎬 Video length: `{_format_duration(video_duration)}`\n"
                f"⏱️ Elapsed: `{_format_duration(elapsed)}`"
            )
        )
        reasons_text = ", ".join(e.reasons[:4]) if e.reasons else "low-signal transcript"
        comparison_explainer = ""
        match = re.search(r"\((\d+(?:\.\d+)?)<(\d+(?:\.\d+)?)\)", reasons_text)
        if match:
            detected = match.group(1)
            required = match.group(2)
            comparison_explainer = (
                f" (The detected transcript-caption topic overlap is {detected}, "
                f"but the minimum required is {required}.)"
            )
        else:
            overlap_ratio = (e.metrics or {}).get("caption", {}).get("overlap_ratio")
            if isinstance(overlap_ratio, (int, float)):
                min_overlap = max(0.0, min(1.0, float(os.getenv("TRANSCRIPT_CAPTION_MIN_OVERLAP", "0.08"))))
                comparison_explainer = (
                    f" (Detected transcript-caption topic overlap is {overlap_ratio:.2f}, "
                    f"minimum required is {min_overlap:.2f}.)"
                )
        view = TryAnywayView(
            url=clean_url,
            requester_id=interaction.user.id,
            guild_id=interaction.guild.id if interaction.guild else 0,
        )
        await interaction.followup.send(
            f"No transcript detected (due to {reasons_text}){comparison_explainer}. "
            "Click **Try anyway** to force summarization.",
            view=view,
        )
    except Exception as e:
        stop_updater.set()
        await updater_task
        elapsed = time.monotonic() - started
        await status_message.edit(
            content=(
                "❌ NORA failed while processing.\n"
                f"🎬 Video length: `{_format_duration(video_duration)}`\n"
                f"⏱️ Elapsed: `{_format_duration(elapsed)}`"
            )
        )
        await interaction.followup.send(
            f"Failed to process link: `{_truncate_err(e)}`\n"
            f"Runtime before failure: `{_format_duration(elapsed)}`"
        )


@tree.command(name="saveall", description="Process previous Instagram links in this channel.")
@app_commands.describe(
    max_messages="How many recent messages to scan (default 500)",
    max_new_links="How many new links to process this run (default 50)",
    oldest_first="Scan oldest to newest first",
)
async def saveall(
    interaction: discord.Interaction,
    max_messages: Optional[int] = None,
    max_new_links: Optional[int] = None,
    oldest_first: bool = True,
):
    channel = interaction.channel
    guild = interaction.guild
    if channel is None:
        await interaction.response.send_message("No channel context is available.", ephemeral=True)
        return
    if guild is None:
        await interaction.response.send_message("`/saveall` is only supported in servers.", ephemeral=True)
        return

    requested_max_messages = max_messages if max_messages is not None else SAVEALL_DEFAULT_MAX_MESSAGES
    requested_max_new_links = max_new_links if max_new_links is not None else SAVEALL_DEFAULT_MAX_NEW_LINKS

    max_messages_final = max(1, min(requested_max_messages, SAVEALL_HARD_MAX_MESSAGES))
    max_new_links_final = max(1, min(requested_max_new_links, SAVEALL_HARD_MAX_NEW_LINKS))

    me = guild.me or guild.get_member(client.user.id if client.user else 0)
    perms = channel.permissions_for(me) if me else None
    if not perms or not perms.read_message_history or not perms.view_channel:
        await interaction.response.send_message(
            "I need View Channel + Read Message History permissions in this channel.",
            ephemeral=True,
        )
        return

    lock = _guild_lock(guild.id)
    if lock.locked():
        await interaction.response.send_message(
            "A `/saveall` job is already running for this server. Try again shortly.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    scanned_messages = 0
    found_links = 0
    processed_count = 0
    skipped_count = 0
    failed_count = 0

    already_processed = get_processed_urls()
    processed_urls_this_run: set[str] = set()

    async with lock:
        try:
            async for message in channel.history(limit=max_messages_final, oldest_first=oldest_first):
                scanned_messages += 1
                if message.author.bot:
                    continue

                urls = _extract_instagram_urls(message.content or "")
                if not urls:
                    continue

                for url in urls:
                    found_links += 1

                    if url in processed_urls_this_run:
                        skipped_count += 1
                        continue
                    if url in already_processed:
                        skipped_count += 1
                        continue

                    if processed_count >= max_new_links_final:
                        break

                    try:
                        note_path = await asyncio.to_thread(process_instagram_link, url)
                        already_processed.add(url)
                        processed_urls_this_run.add(url)
                        processed_count += 1
                        if processed_count % max(1, SAVEALL_PROGRESS_EVERY) == 0:
                            await interaction.followup.send(
                                f"Progress: processed {processed_count} links so far. Latest note: `{note_path}`"
                            )
                    except LowTranscriptSignalError:
                        skipped_count += 1
                    except Exception:
                        failed_count += 1

                if processed_count >= max_new_links_final:
                    break
        except Exception as e:
            await interaction.followup.send(f"`/saveall` failed while scanning history: `{_truncate_err(e)}`")
            return

    summary = (
        "Done with `/saveall`.\n"
        f"- Scanned messages: {scanned_messages}\n"
        f"- Instagram links found: {found_links}\n"
        f"- Processed new links: {processed_count}\n"
        f"- Skipped already-processed/duplicate links: {skipped_count}\n"
        f"- Failed: {failed_count}\n"
        f"- Limits used: max_messages={max_messages_final}, max_new_links={max_new_links_final}"
    )
    await interaction.followup.send(summary)


client.run(TOKEN)
