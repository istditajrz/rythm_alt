import discord, re, os, json, asyncio
from discord.ext import commands, tasks
from discord_slash import cog_ext, SlashCommandOptionType, SlashContext
from discord_slash.client import SlashCommand
import youtube_dl
from discord_slash.utils.manage_commands import create_option


class yt(commands.Cog):
    URL_REGEX = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    EMBED_FORMAT = """{{
    'author': {{
        'icon_url': '{author_icon}',
        'name': 'Added to queue',
        'proxy_icon_url': '{author_icon_proxy}',
        'url': 'https://takeb1nzyto.space/'
    }},
    'description': '**[{video_title}]({video_url})**',
    'fields': [
        {{'inline': true, 'name': 'Channel', 'value': '{channel}'}},
        {{'inline': true, 'name': 'Song Duration', 'value': '{duration}'}},
        {{'inline': true, 'name': 'Estimated time until playing', 'value': '{time_until_play}'}},
        {{'inline': true, 'name': 'Position in queue', 'value': '{pos_in_queue}'}}
    ],
    'thumbnail': {{
        'height': {thumbnail_height},
        'url': '{thumbnail_url}',
        'width': {thumbnail_width}
    }},
    'type': 'rich'
    }}""".replace('\'', '\"').replace('\n', '').replace(" " * 4, " ")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ydl = youtube_dl.YoutubeDL({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            "outtmpl" : '.\\assets\\%(id)s.%(ext)s'
        })
        self.voice_client = None
        self.queue = []
        self.delete = []
        self._play.start()
        
    
    @staticmethod
    def duration_formating(s: int) -> str:
        h = str((s // 60) // 60)
        m = str((s // 60) % 60)
        s = str(s % 60)
        return "{}:{}:{}".format(h.zfill(2), m.zfill(2), s.zfill(2)) if h != '0' else "{}:{}".format(m.zfill(2), s.zfill(2))

    async def _join(self, ctx: SlashContext):
        if self.voice_client == None:
            # if voice client isn't already connected

            for channel in ctx.guild.voice_channels:
                # every voice channel in the server
                if ctx.author in channel.members:
                    # if the author is in a vc stop and join it
                    self.voice_client = await channel.connect()
                    return
            if self.voice_client == None:
                await ctx.send(
                    "You are not in a vc or I cannot see the vc, join a visible vc to begin."
                )
                return
        else:
            await ctx.send("already in a vc")

    @cog_ext.cog_slash(name='join', description="bring the bot to your vc")
    async def join(self, ctx: SlashContext):
        await self._join(ctx)
        await ctx.send("Joined!")

    @cog_ext.cog_slash(
        name="play", 
        description="Add a song to the queue",
        options=[
            create_option("song", "song (url) to add to queue", SlashCommandOptionType.STRING, True, None)
        ]
        )
    async def play(self, ctx: SlashContext, song: str) -> None:
        if self.voice_client == None:
            await self._join(ctx)
        if ctx.author not in self.voice_client.channel.members:
            return await ctx.send("You're not in the voice channel")
        await ctx.defer()
        if re.match(self.URL_REGEX, song) is None:
            with self.ydl as ydl:
                result = ydl.extract_info(f"ytsearch:{song}")
        with self.ydl as ydl:
            result = ydl.extract_info(song)
        duration_to_play = sum([v[1] for v in self.queue])
        pos_in_queue = len(self.queue)
        self.queue.append(
            (
                discord.FFmpegPCMAudio(
                    ".\\assets\\" + str(result['id']) + '.mp3', 
                    executable="./ffmpeg.exe", 
                    before_options=("-guess_layout_max 0")
                ),
                result['duration'],
                ".\\assets\\" + str(result['id']) + '.mp3'
            )
        )

        await ctx.send(
            embed=discord.Embed.from_dict(
                json.loads(
                    self.EMBED_FORMAT.format(
                        author_icon = ctx.author.avatar_url,
                        author_icon_proxy = ctx.author.default_avatar_url,
                        video_title = result['title'],
                        video_url = result['webpage_url'],
                        channel = result['channel'],
                        duration = self.duration_formating(result['duration']),
                        time_until_play = self.duration_formating(duration_to_play),
                        pos_in_queue = pos_in_queue,
                        thumbnail_height = result['thumbnails'][0]['height'],
                        thumbnail_url = result['thumbnails'][0]['url'],
                        thumbnail_width = result['thumbnails'][0]['height']
                    )
                )
            )
        )
        

    @tasks.loop(seconds=10)
    async def _play(self):
        for file in self.delete:
            try:
                os.remove(file)
                self.delete.remove(file)
            except PermissionError as e:
                print(e)
        if len(self.queue) < 1:
            return
        if self.voice_client is None:
            self.queue.clear()
            return
        if not self.voice_client.is_playing():
            new = self.queue.pop(0)
            self.voice_client.play(new[0])
            print('playing')
            await asyncio.sleep(2)
            self.delete.append(new[2])

if __name__ == '__main__':
    bot = commands.Bot('@', intents=discord.Intents.all())
    slash = SlashCommand(bot, sync_commands=True)
    bot.add_cog(yt(bot))
    print('Added Cog')
    @bot.event
    async def on_ready():
        print(f'Logged in {bot.user!s} ({bot.user.id})')
