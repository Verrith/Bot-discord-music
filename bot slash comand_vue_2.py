import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# ================== ENV ==================
load_dotenv()
TOKEN = os.getenv("TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not TOKEN:
    raise ValueError("❌ Aucun TOKEN trouvé dans .env !")

# Spotify client
sp = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    ))

# ================== INTENTS & BOT ==================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================== YT-DLP ==================
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'geo_bypass': True,
    'ignoreerrors': True,
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

def find_ffmpeg():
    local_path = os.path.join(os.getcwd(), "bin", "ffmpeg.exe")
    if os.path.isfile(local_path):
        return local_path
    return "ffmpeg"

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1.0):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")

    @classmethod
    async def from_url(cls, url, *, loop=None, volume=1.0):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except Exception as e:
            raise RuntimeError(f"Erreur yt-dlp : {e}")

        if not data:
            raise RuntimeError("yt-dlp n'a rien retourné")
        if 'entries' in data:
            data = data['entries'][0]

        formats = data.get('formats')
        audio_url = None
        if formats:
            for f in formats:
                if f.get('acodec') != 'none':
                    audio_url = f.get('url')
                    break
        else:
            audio_url = data.get("url")
        if not audio_url:
            raise RuntimeError("Impossible d'obtenir l'URL audio pour FFmpeg")

        ffmpeg_path = find_ffmpeg()
        source = discord.FFmpegPCMAudio(
            audio_url,
            executable=ffmpeg_path,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin",
            options="-vn"
        )
        return cls(source, data=data, volume=volume)

# ================== UTILS ==================
def is_spotify_url(url: str) -> bool:
    return "spotify.com" in url

def is_soundcloud_url(url: str) -> bool:
    return "soundcloud.com" in url or "snd.sc" in url

async def spotify_to_tracks(url: str):
    if sp is None:
        return None
    results = []
    if "track" in url:
        track = sp.track(url)
        results.append({
            "query": f"{track['name']} {track['artists'][0]['name']}",
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "thumbnail": (track["album"]["images"][0]["url"] if track["album"]["images"] else None),
            "duration": track["duration_ms"] // 1000,
            "source": "spotify",
        })
    elif "album" in url:
        album = sp.album(url)
        album_thumb = album["images"][0]["url"] if album["images"] else None
        for t in album["tracks"]["items"]:
            results.append({
                "query": f"{t['name']} {t['artists'][0]['name']}",
                "title": t["name"],
                "artist": t["artists"][0]["name"],
                "thumbnail": album_thumb,
                "duration": t.get("duration_ms", 0) // 1000,
                "source": "spotify",
            })
    elif "playlist" in url:
        playlist = sp.playlist(url)
        for item in playlist["tracks"]["items"]:
            track = item.get("track")
            if not track:
                continue
            results.append({
                "query": f"{track['name']} {track['artists'][0]['name']}",
                "title": track["name"],
                "artist": track["artists"][0]["name"],
                "thumbnail": (track["album"]["images"][0]["url"] if track["album"]["images"] else None),
                "duration": track.get("duration_ms", 0) // 1000,
                "source": "spotify",
            })
    return results

# ================== MUSIC PLAYER ==================
class MusicPlayer:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.queue = []
        self.playing = False

    async def play_next(self):
        if not self.queue or self.interaction.guild.voice_client is None:
            self.playing = False
            return

        self.playing = True
        track = self.queue.pop(0)
        url_to_play = track.get("url") or track.get("query") or track.get("title")

        try:
            player = await YTDLSource.from_url(url_to_play, volume=1.0)
        except Exception as e:
            await self.interaction.followup.send(f"❌ Impossible de lire : {e}")
            self.playing = False
            await self.play_next()
            return

        def after(_):
            coro = self.play_next()
            asyncio.run_coroutine_threadsafe(coro, bot.loop)

        self.interaction.guild.voice_client.play(player, after=after)

        # Couleurs
        if track.get("source") == "spotify":
            color = 0x1DB954
            source_label = "Spotify"
        elif track.get("source") == "soundcloud":
            color = 0xFF7700
            source_label = "SoundCloud"
        else:
            color = 0xFF0000
            source_label = "YouTube"

        embed = discord.Embed(
            title="🎵 Lecture en cours",
            description=f"**{track.get('title', player.title)}**",
            color=color
        )

        # Thumbnail sous le titre
        thumb = track.get("thumbnail") or player.data.get("thumbnail")
        if thumb:
            embed.set_image(url=thumb)

        # Infos en dessous
        artist = track.get("artist") or player.data.get("uploader")
        if artist:
            embed.add_field(name="👤 Artiste", value=artist, inline=True)
        duration_val = track.get("duration") or player.data.get("duration")
        if duration_val:
            minutes = int(duration_val // 60)
            seconds = int(duration_val % 60)
            embed.add_field(name="⏱️ Durée", value=f"{minutes}:{seconds:02d}", inline=True)
        embed.add_field(name="🔗 Source", value=source_label, inline=True)
        embed.set_footer(text="🎧 nom_de_ton_bot")
        await self.interaction.followup.send(embed=embed)

    async def add_to_queue(self, item):
        if isinstance(item, dict):
            track = item
        else:
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(item, download=False))
                if "entries" in data:
                    data = data["entries"][0]
                title = data.get("title", item)
                thumb = data.get("thumbnail")
                uploader = data.get("uploader")
                duration = data.get("duration")
                extractor = data.get("extractor_key", "").lower()
            except Exception:
                title, thumb, uploader, duration, extractor = item, None, None, None, ""
            source = "soundcloud" if "soundcloud" in extractor else "yt"
            track = {
                "url": item,
                "title": title,
                "thumbnail": thumb,
                "artist": uploader,
                "duration": duration,
                "source": source,
            }

        if self.playing:
            self.queue.append(track)
            await self.interaction.followup.send(f"➕ Ajouté à la file : **{track['title']}**")
        else:
            self.queue.append(track)
            await self.play_next()

# ================== PLAYERS ==================
players = {}
def get_player(interaction: discord.Interaction):
    if interaction.guild.id not in players:
        players[interaction.guild.id] = MusicPlayer(interaction)
    else:
        players[interaction.guild.id].interaction = interaction
    return players[interaction.guild.id]

# ================== SLASH COMMANDS ==================
@tree.command(name="play", description="🔊 Joue une musique ou l'ajoute à la file d'attente")
async def slash_play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    if interaction.user.voice is None:
        return await interaction.followup.send("⚠️ Tu dois être dans un salon vocal !")
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client is None:
        await channel.connect()
    else:
        await interaction.guild.voice_client.move_to(channel)

    if is_spotify_url(url):
        tracks = await spotify_to_tracks(url)
        if tracks is None:
            return await interaction.followup.send("⚠️ Identifiants Spotify manquants dans .env")
        if not tracks:
            return await interaction.followup.send("⚠️ Impossible de lire le lien Spotify.")
        for t in tracks:
            await get_player(interaction).add_to_queue(t)
        return

    if is_soundcloud_url(url):
        await get_player(interaction).add_to_queue(url)
        return

    await get_player(interaction).add_to_queue(url)

@tree.command(name="skip", description="⏭️ Passe la musique en cours")
async def slash_skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Musique passée !")
    else:
        await interaction.response.send_message("⚠️ Aucune musique à skip.")

@tree.command(name="pause", description="⏸️ Met la musique en pause")
async def slash_pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Musique mise en pause.")
    else:
        await interaction.response.send_message("⚠️ Pas de musique à mettre en pause.")

@tree.command(name="resume", description="▶️ Reprend la musique en pause")
async def slash_resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Musique reprise.")
    else:
        await interaction.response.send_message("⚠️ Aucune musique en pause.")

@tree.command(name="stop", description="⏹️ Stoppe la musique et déconnecte le bot")
async def slash_stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        players.pop(interaction.guild.id, None)
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ Déconnecté et file effacée.")
    else:
        await interaction.response.send_message("⚠️ Le bot n'est pas connecté.")

@tree.command(name="queue", description="📜 Affiche la file d'attente")
async def slash_queue(interaction: discord.Interaction):
    await interaction.response.defer()
    player = get_player(interaction)
    if not player.queue:
        return await interaction.followup.send("📭 La file est vide.")

    for i, track in enumerate(player.queue, 1):
        embed = discord.Embed(
            title=f"{i}. {track.get('title','Titre inconnu')}",
            color=0x5865F2
        )

        # Thumbnail sous le titre
        thumb = track.get("thumbnail")
        if thumb:
            embed.set_image(url=thumb)

        # Infos en dessous
        artist = track.get("artist","Artiste inconnu")
        duration_val = track.get("duration")
        duration_str = f"{int(duration_val//60)}:{int(duration_val%60):02d}" if duration_val else "❓"
        source_label = track.get("source","YouTube/Recherche").capitalize()
        embed.add_field(name="👤 Artiste", value=artist, inline=True)
        embed.add_field(name="⏱️ Durée", value=duration_str, inline=True)
        embed.add_field(name="🔗 Source", value=source_label, inline=True)
        embed.set_footer(text="🎧 File d'attente de nom_de_ton_bot")
        await interaction.followup.send(embed=embed)

@tree.command(name="help", description="❓ Affiche toutes les commandes disponibles")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎵 Commandes du Bot Musique",
        description="Voici toutes les commandes disponibles :",
        color=0x5865F2
    )
    for command in tree.get_commands():
        description = command.description if command.description else "Pas de description"
        embed.add_field(name=f"/{command.name}", value=description, inline=False)
    embed.set_footer(text="🎧 nom_de_ton_bot")
    await interaction.response.send_message(embed=embed)

# ================== ON READY ==================
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="DJ Twahlett 🎧"
        )
    )
    await tree.sync()
    print(f"✅ Connecté en tant que {bot.user}")

bot.run(TOKEN)
