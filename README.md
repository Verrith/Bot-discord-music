# 1- installation des application
[python 3.12](https://www.python.org/downloads/windows/) - minimum<br>
[ffmpeg](https://www.ffmpeg.org/download.html) - vous devrier prendre le ffmpeg-git-full.7z

# 2- création du bot
créer votre bot sur [discord dev](https://discord.com/developers/applications)<br>
récupérer votre token ici
- BOT <br>
- Reset Token <br>
- copier Token <br>
- collez votre token sur le `.env` <br>
créer votre application sur <a href="https://developer.spotify.com/dashboard/create">spotify dev</a><br>
- en Redirect URIs mettez ceci: `https://example.com/callback` <br><br>

récupérer le Client ID et Client secret sur vottre application <br>
- copier les numéro de ton Client ID et posé le dans le `.env` avec le nom CLIENT_ID <br>
- même chose avec le Client secret

# 3- le set up
décomprésser ffmpeg et renomé le dossier ffmpeg et mettez le dans le C:\
ça devrais recembler a ceci C:\ffmpeg\ <br>
<img src="images/Capture d’écran 2025-11-27 141219.png" alt="image d'exemple" width="500"/>

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

# 4- lancement du bot
quand vous avez tout fait coisisez un code entre les 4 <br><br>

## 1. les slash
c'est pour que ton bot prennent les `/play` et autre.<br><br>

## 2. les autre qui on pas le nom slash
vous pouvez changer le prefix des comande que pour le moment c un point d'exclamation.<br>
ex. `!play`<br><br>

## 3. les affichage diférent
### 1. vue 1

### 2. vue 2
<h2>sur spotify</h2>
<img src="images/visuel2 spotify.png" alt="spotify" width="500"/>
<h3>sur soundcloud</h3>
<img src="images/visuel2 soundcloud.png" alt="soundcloud" width="500"/>
<h3>youtube</h3>
<img src="images/visuel2 youtube.png" alt="youtube" width="500"/>
