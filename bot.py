import asyncio
import logging
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
SAVEALL_FALLBACK_CHANNEL_MESSAGE = os.getenv("SAVEALL_FALLBACK_CHANNEL_MESSAGE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
}
SAVEALL_EDIT_ORIGINAL_PROGRESS = os.getenv("SAVEALL_EDIT_ORIGINAL_PROGRESS", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
}
DISCORD_MESSAGE_CHAR_LIMIT = 2000
DISCORD_SAFE_MESSAGE_LEN = 1900

logger = logging.getLogger(__name__)


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


def _truncate_for_discord(content: str, max_len: int = DISCORD_SAFE_MESSAGE_LEN) -> str:
    text = (content or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _build_saveall_summary(
    *,
    scanned_messages: int,
    found_links: int,
    processed_count: int,
    skipped_count: int,
    failed_count: int,
    max_messages_final: int,
    max_new_links_final: int,
    latest_note_path: Optional[str],
    scan_error: Optional[str],
) -> str:
    parts = [
        "Done with `/saveall`.",
        f"- Scanned messages: {scanned_messages}",
        f"- Instagram links found: {found_links}",
        f"- Processed new links: {processed_count}",
        f"- Skipped already-processed/duplicate links: {skipped_count}",
        f"- Failed: {failed_count}",
        f"- Limits used: max_messages={max_messages_final}, max_new_links={max_new_links_final}",
    ]
    if latest_note_path:
        parts.append(f"- Latest note: `{latest_note_path}`")
    if scan_error:
        parts.append(f"- Scan interrupted: `{scan_error}`")
    return "\n".join(parts)


def _log_saveall_summary(
    *,
    guild_id: int,
    channel_id: int,
    scanned_messages: int,
    found_links: int,
    processed_count: int,
    skipped_count: int,
    failed_count: int,
    latest_note_path: Optional[str],
    scan_error: Optional[str],
    progress_updates: int,
    discord_delivery: str,
) -> None:
    lines = [
        "[SAVEALL] SUMMARY",
        f"guild_id={guild_id} channel_id={channel_id}",
        f"counts scanned={scanned_messages} found={found_links} processed={processed_count} skipped={skipped_count} failed={failed_count}",
        f"progress_updates={progress_updates}",
        f"latest_note={latest_note_path or '(none)'}",
        f"scan_error={scan_error or '(none)'}",
        f"discord_delivery={discord_delivery}",
    ]
    block = "\n".join(lines)
    logger.info(block)
    print(block)


async def _send_saveall_update(
    *,
    interaction: discord.Interaction,
    channel: discord.abc.Messageable,
    content: str,
    me: Optional[discord.Member],
    allow_channel_fallback: bool,
) -> str:
    payload = _truncate_for_discord(content)
    use_edit = SAVEALL_EDIT_ORIGINAL_PROGRESS
    if use_edit:
        try:
            await interaction.edit_original_response(content=payload)
            return "edit_original_response:ok"
        except discord.HTTPException as e:
            logger.warning(
                "saveall edit_original_response failed status=%s code=%s message=%s",
                getattr(e, "status", None),
                getattr(e, "code", None),
                _truncate_err(e),
            )
            if not allow_channel_fallback or not SAVEALL_FALLBACK_CHANNEL_MESSAGE:
                return f"edit_original_response:failed(status={getattr(e, 'status', 'n/a')},code={getattr(e, 'code', 'n/a')})"
    try:
        await interaction.followup.send(payload)
        return "followup_send:ok"
    except discord.HTTPException as e:
        logger.warning(
            "saveall followup.send failed status=%s code=%s message=%s",
            getattr(e, "status", None),
            getattr(e, "code", None),
            _truncate_err(e),
        )
        if not allow_channel_fallback or not SAVEALL_FALLBACK_CHANNEL_MESSAGE:
            return f"followup_send:failed(status={getattr(e, 'status', 'n/a')},code={getattr(e, 'code', 'n/a')})"
        try:
            can_send = hasattr(channel, "send")
            if me and hasattr(channel, "permissions_for"):
                perms = channel.permissions_for(me)  # type: ignore[attr-defined]
                can_send = bool(perms and perms.send_messages)
            if can_send:
                await channel.send(
                    _truncate_for_discord(
                        "[saveall] Interaction delivery failed; posting summary in channel.\n\n" + payload,
                        max_len=DISCORD_MESSAGE_CHAR_LIMIT,
                    )
                )
                return "channel_send_fallback:ok"
            return "channel_send_fallback:skipped(no_permission)"
        except Exception as channel_err:
            logger.warning("saveall channel fallback send failed: %s", _truncate_err(channel_err))
            return f"channel_send_fallback:failed({type(channel_err).__name__})"


async def _safe_defer(interaction: discord.Interaction, *, thinking: bool = True) -> bool:
    if interaction.response.is_done():
        return False
    try:
        await interaction.response.defer(thinking=thinking)
        return True
    except discord.HTTPException as e:
        # Another response path can occasionally acknowledge first.
        if getattr(e, "code", None) == 40060:
            logger.warning("Interaction already acknowledged before defer (code=40060).")
            return False
        raise


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

        await _safe_defer(interaction, thinking=True)
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

    await _safe_defer(interaction, thinking=True)

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

    await _safe_defer(interaction, thinking=True)

    scanned_messages = 0
    found_links = 0
    processed_count = 0
    skipped_count = 0
    failed_count = 0
    progress_updates = 0
    latest_note_path: Optional[str] = None
    scan_error: Optional[str] = None

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
                        latest_note_path = str(note_path)
                        if processed_count % max(1, SAVEALL_PROGRESS_EVERY) == 0:
                            progress_updates += 1
                            await _send_saveall_update(
                                interaction=interaction,
                                channel=channel,
                                me=me,
                                allow_channel_fallback=False,
                                content=(
                                    "Running `/saveall`...\n"
                                    f"- Processed so far: {processed_count}\n"
                                    f"- Failed so far: {failed_count}\n"
                                    f"- Scanned messages so far: {scanned_messages}\n"
                                    f"- Latest note: `{note_path}`"
                                ),
                            )
                    except LowTranscriptSignalError:
                        skipped_count += 1
                    except Exception:
                        failed_count += 1

                if processed_count >= max_new_links_final:
                    break
        except Exception as e:
            scan_error = _truncate_err(e)

    summary = _build_saveall_summary(
        scanned_messages=scanned_messages,
        found_links=found_links,
        processed_count=processed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        max_messages_final=max_messages_final,
        max_new_links_final=max_new_links_final,
        latest_note_path=latest_note_path,
        scan_error=scan_error,
    )
    discord_delivery = await _send_saveall_update(
        interaction=interaction,
        channel=channel,
        me=me,
        allow_channel_fallback=True,
        content=summary,
    )
    _log_saveall_summary(
        guild_id=guild.id,
        channel_id=channel.id,
        scanned_messages=scanned_messages,
        found_links=found_links,
        processed_count=processed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        latest_note_path=latest_note_path,
        scan_error=scan_error,
        progress_updates=progress_updates,
        discord_delivery=discord_delivery,
    )


client.run(TOKEN)
