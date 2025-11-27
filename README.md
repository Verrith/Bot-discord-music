# 1- installation des application
[python 3.12](https://www.python.org/downloads/windows/) - minimum<br>
[ffmpeg](https://www.ffmpeg.org/download.html) - vous devrier prendre le ffmpeg-git-full.7z

# 2-
créer votre bot sur [discord dev](https://discord.com/developers/applications)<br>
récupérer votre token ici
- BOT <br>
- Reset Token <br>
- copier Token
<br>
créer votre application sur <a href="https://developer.spotify.com/dashboard/create">spotify dev</a><br>


# 3- le set up
décomprésser ffmpeg et renomé le dossier ffmpeg et mettez le dans le C:\
ça devrais recembler a ceci C:\ffmpeg\ <br>
<img src="images/Capture d’écran 2025-11-27 141219.png" alt="Texte alternatif" width="500"/>

### 1.Modifier les variables d’environnement
allez sur `Modifier les variables d’environnement système`<br>
- avancer<br>
- variable d'environnement<br>
- path / modifier<br>
- nouveau<br>
- mettez ceci: `C:\ffmpeg\bin`

### 2. Installation des programme sur python
allez sur cmd avec l'aide de la touche windows <br><br>

`python -m pip install -U git+https://github.com/yt-dlp/yt-dlp.git` <br>
`python -m pip install -U discord.py` <br>
`pip install -U yt-dlp` <br>
`pip install python-dotenv` <br>
`pip install pynacl` <br>
`pip install discord.py yt-dlp spotipy python-dotenv` <br>
`pip install mutagen` <br>
`pip install pycryptodomex` <br>
`pip install spotipy`