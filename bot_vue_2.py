import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Charger .env
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

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

# yt-dlp options
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

# Classe YTDLSource
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

def is_spotify_url(url: str) -> bool:
    return "spotify.com" in url

def is_soundcloud_url(url: str) -> bool:
    return "soundcloud.com" in url or "snd.sc" in url

# Spotify → pistes
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

# MusicPlayer
class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.queue = []
        self.playing = False

    async def play_next(self):
        if not self.queue or self.ctx.voice_client is None:
            self.playing = False
            return

        self.playing = True
        track = self.queue.pop(0)

        url_to_play = track.get("url") or track.get("query") or track.get("title")

        try:
            player = await YTDLSource.from_url(url_to_play, volume=1.0)
        except Exception as e:
            await self.ctx.send(f"❌ Impossible de lire : {e}")
            self.playing = False
            await self.play_next()
            return

        def after(_):
            coro = self.play_next()
            asyncio.run_coroutine_threadsafe(coro, bot.loop)

        self.ctx.voice_client.play(player, after=after)

        # Couleurs embed
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

        # Image grande sous le texte
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
        await self.ctx.send(embed=embed)

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
            await self.ctx.send(f"➕ Ajouté à la file : **{track['title']}**")
        else:
            self.queue.append(track)
            await self.play_next()

players = {}
def get_player(ctx):
    if ctx.guild.id not in players:
        players[ctx.guild.id] = MusicPlayer(ctx)
    return players[ctx.guild.id]

# ===== COMMANDES =====
@bot.command(help="🔊 Joue une musique ou l'ajoute à la file d'attente")
async def play(ctx, *, url: str):
    if ctx.author.voice is None:
        return await ctx.send("⚠️ Tu dois être dans un salon vocal !")

    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    else:
        await ctx.voice_client.move_to(channel)

    # Spotify
    if is_spotify_url(url):
        tracks = await spotify_to_tracks(url)
        if tracks is None:
            return await ctx.send("⚠️ Identifiants Spotify manquants dans .env")
        if not tracks:
            return await ctx.send("⚠️ Impossible de lire le lien Spotify.")
        for t in tracks:
            await get_player(ctx).add_to_queue(t)
        return

    # SoundCloud
    if is_soundcloud_url(url):
        await get_player(ctx).add_to_queue(url)
        return

    # YouTube + recherche auto
    await get_player(ctx).add_to_queue(url)

@bot.command(help="⏭️ Passe la musique en cours")
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Musique passée !")
    else:
        await ctx.send("⚠️ Aucune musique à skip.")

@bot.command(help="⏸️ Met la musique en pause")
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Musique mise en pause.")
    else:
        await ctx.send("⚠️ Pas de musique à mettre en pause.")

@bot.command(help="▶️ Reprend la musique en pause")
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Musique reprise.")
    else:
        await ctx.send("⚠️ Aucune musique en pause.")

@bot.command(help="📜 Affiche la file d'attente")
async def queue(ctx):
    player = get_player(ctx)
    if not player.queue:
        return await ctx.send("📭 La file est vide.")

    for i, track in enumerate(player.queue, 1):
        title = track.get("title", "Titre inconnu")
        artist = track.get("artist")
        thumb = track.get("thumbnail")
        duration_val = track.get("duration")

        if track.get("source") == "spotify":
            color = 0x1DB954
            source_label = "Spotify"
        elif track.get("source") == "soundcloud":
            color = 0xFF7700
            source_label = "SoundCloud"
        else:
            color = 0xFF0000
            source_label = "YouTube/Recherche"

        embed = discord.Embed(
            title=f"{i}. 🎶 {title}",
            color=color
        )

        # Image plus grande sous le texte
        if thumb:
            embed.set_image(url=thumb)

        # Infos
        if artist:
            embed.add_field(name="👤 Artiste", value=artist, inline=True)
        if duration_val:
            minutes = int(duration_val // 60)
            seconds = int(duration_val % 60)
            embed.add_field(name="⏱️ Durée", value=f"{minutes}:{seconds:02d}", inline=True)

        embed.add_field(name="🔗 Source", value=source_label, inline=True)
        embed.set_footer(text="🎧 File d'attente de nom_de_ton_bot")
        await ctx.send(embed=embed)

@bot.command(help="🗑️ Vide la file d'attente")
async def clear(ctx):
    player = get_player(ctx)
    player.queue.clear()
    await ctx.send("🗑️ File d'attente vidée.")

@bot.command(help="⏹️ Stoppe la musique et déconnecte le bot")
async def stop(ctx):
    if ctx.voice_client:
        players.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Déconnecté et file effacée.")
    else:
        await ctx.send("⚠️ Le bot n'est pas connecté.")

@bot.command(help="❓ Affiche toutes les commandes disponibles")
async def help(ctx):
    embed = discord.Embed(
        title="🎵 Commandes du Bot Musique",
        description="Voici toutes les commandes disponibles :",
        color=0x5865F2
    )
    for command in bot.commands:
        description = command.help if command.help else "Pas de description"
        embed.add_field(name=f"!{command.name}", value=description, inline=False)
    embed.set_footer(text="🎧 nom_de_ton_bot")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="DJ Twahlett 🎧"
        )
    )
    print(f"✅ Connecté en tant que {bot.user}")

bot.run(TOKEN)
