import asyncio
import datetime
import logging
import os
import re
import sys
from typing import Union, Callable, Coroutine
from webbrowser import get

import discord
import gtts.tokenizer.symbols
from discord.ext import commands
from gtts import gTTS as googleTTS
# from TTS import tts as TTS

from logging import config as lonfig

lonfig.dictConfig(
	{
		"version": 1,
		'disable_existing_loggers': False,
		"formatters": {
			"default": {
				"format": "[%(asctime)s] [%(threadName)s|%(name)-16s/%(levelname)-8s] %(message)s"
			},
			"brief": {
				"format": "%(levelname)-8s: %(message)s"
			}
		},
		'handlers': {
			"console": {
				"class": "logging.StreamHandler",
				"formatter": "brief",
				"stream": sys.stdout,
				"level": 0 if False else "INFO"
			},
			"info": {
				"class": "logging.FileHandler",
				"filename": f'logs/latest.log',
				"formatter": "default",
				"level": "INFO"
			},
			"verbose": {
				"class": "logging.FileHandler",
				"filename": f'logs/debug_latest.log',
				"formatter": "default"
			}
		},
		"loggers": {
			'': {
				"level": 0,
				"handlers": [
					"console",
					"verbose",
					"info"
				]
			}
		}
	}
)

class SourceWithExtra:
	def __init__(self, user, file, source):
		self.user = user
		self.file = file
		self.source = source


logging.captureWarnings(True)
logger = logging.getLogger("bot.main")

bot = commands.Bot(command_prefix="!", description='Simple TTS bot', intents=discord.Intents.all())

sources = {}
last_users = {}
files = {}
current_source = {}

settings = {}

settings_path = "settings.json"

translations = {
	"ru": {
		"code_block": " кусок кода ",
		"code_block_with_lang": " кусок кода на {}",
		"link": " ссылка на {} ",
		"role": " роль {} ",
	},
	"en": {
		"code_block": " code block ",
		"code_block_with_lang": " code block on {}",
		"link": " link to {} ",
		"role": " role {} ",
	},
}

gtts.tokenizer.symbols.SUB_PAIRS += (
	(re.compile(r'\btbh\b'), 'to be honest'),
	(re.compile(r'\bngl\b'), 'not gonna lie'),
	(re.compile(r'\bwtf\b'), 'what the f'),
	(re.compile(r'\bnggyu\b'), '''Never gonna give you up
Never gonna let you down
Never gonna run around and desert you
Never gonna make you cry
Never gonna say goodbye
Never gonna tell a lie and hurt you
'''),
	(re.compile(r'\bcya\b'), 'see ya'),
	(re.compile(r'\bnya'), 'nyaa'),
	(re.compile(r'\b101\b'), '1 o 1'),
	(re.compile(r'\bikr\b'), 'i know, really'),
	(re.compile(r'\bmhm'), 'hmm'),
	(re.compile(r'\big\b'), 'i guess'),
	(re.compile(r'\bidk\b'), "i don't know"),
	(re.compile(r'\brn\b'), 'right now'),
	(re.compile(r'\bim\b'), 'I\'m')
)


def load():
	global settings
	print("loaded")
	with open(settings_path, "r") if os.path.exists(settings_path) else open(settings_path, "x+") as settings_file:
		import json
		try:
			settings = json.load(settings_file)
		except json.JSONDecodeError as e:
			settings = {}


def save():
	global settings
	with open(settings_path, "w") if os.path.exists(settings_path) else open(settings_path, "x") as settings_file:
		import json
		json.dump(settings, settings_file, indent=2)


load()
save()


@bot.command()
async def join(ctx):
	channel = ctx.author.voice.channel
	await channel.connect()


@bot.command()
async def leave(ctx):
	await ctx.voice_client.disconnect()


@bot.group(name="set")
async def settings_group(ctx):
	pass

@settings_group.command(name="channel")
async def chan(context: commands.Context, channel: discord.channel.TextChannel):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {})["channel"] = channel.id
	save()


@settings_group.command(name="require_mute")
async def mute(context: commands.Context, require: bool):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {})["mute-optional"] = not require
	save()


@settings_group.command(name="language")
async def lang(context: commands.Context, lang: str):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {})["lang"] = lang
	save()

@settings_group.group(name="presence_blacklist")
async def presence_blacklist(ctx):
	pass

@presence_blacklist.command(name="enabled")
async def presence_blacklist_enabled(context:commands.Context, enabled: bool):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {}).setdefault("presence_blacklist", {})["enabled"] = enabled
	settings.setdefault(f"{context.guild.id}", {}).setdefault("presence_blacklist", {}).setdefault("ids", [])
	save()

@presence_blacklist.command(name="add")
async def presence_blacklist_add_id(context:commands.Context, user: discord.User):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {}).setdefault("presence_blacklist", {}).setdefault("enabled", True)
	settings.setdefault(f"{context.guild.id}", {}).setdefault("presence_blacklist", {}).setdefault("ids", []).append(user.id)
	save()

@presence_blacklist.command(name="remove")
async def presence_blacklist_remove_id(context:commands.Context, user: discord.User):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {}).setdefault("presence_blacklist", {}).setdefault("enabled", True)
	try:
		settings.setdefault(f"{context.guild.id}", {}).setdefault("presence_blacklist", {}).setdefault("ids", []).remove(user.id)
	except ValueError:
		await context.send(f"User {user} is not in the presence-blacklist")
	finally:
		save()

@settings_group.command(name="usage")
async def usage(context:commands.Context, mode: str):
	if mode in ["whitelist", "blacklist", "unrestricted", "off"]:
		global settings
		load()
		gid = f"{context.guild.id}"
		settings.setdefault(gid, {})["mode"] = mode
		settings[gid].setdefault("whitelist", [])
		settings[gid].setdefault("usage_blacklist", [])
		save()

@settings_group.group(name="usage_blacklist")
async def usage_blacklist(ctx):
	pass

@usage_blacklist.command(name="add")
async def usage_blacklist_add_id(context:commands.Context, user: discord.User):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {}).setdefault("usage_blacklist", []).append(user.id)
	save()

@usage_blacklist.command(name="remove")
async def usage_blacklist_remove_id(context:commands.Context, user: discord.User | discord.Role):
	global settings
	load()
	try:
		settings.setdefault(f"{context.guild.id}", {}).setdefault("usage_blacklist", []).remove(user.id)
	except ValueError:
		await context.send(f"User {user} is not in the usage-blacklist")
	finally:
		save()

@settings_group.group(name="whitelist")
async def whitelist(ctx):
	pass

@whitelist.command(name="add")
async def whitelist_add_id(context:commands.Context, user: discord.User):
	global settings
	load()
	settings.setdefault(f"{context.guild.id}", {}).setdefault("whitelist", []).append(user.id)
	save()

@whitelist.command(name="remove")
async def whitelist_remove_id(context:commands.Context, user: discord.User):
	global settings
	load()
	try:
		settings.setdefault(f"{context.guild.id}", {}).setdefault("whitelist", []).remove(user.id)
	except ValueError:
		await context.send(f"User {user} is not in the usage-whitelist")
	finally:
		save()

expressions = [
	(re.compile(r"```(?P<lang>\w*).*?```", re.DOTALL | re.MULTILINE),
		lambda contents, hit, message, out: translations[settings[f"{message.guild.id}"].setdefault("lang", "en")]["code_block"] if not hit.group("lang") else (
			translations[settings[f"{message.guild.id}"].setdefault("lang", "en")]["code_block_with_lang"].format(hit.group("lang"))
		),
		1), # code blocks
	(re.compile(r"\w+?://(\w+\.)*(?P<domain>\w+)\.(?P<tld>\w+)(?P<path>(/\S*)+)?"),
		lambda contents, hit, message, out: translations[settings[f"{message.guild.id}"].setdefault("lang", "en")]["link"].format(hit.group("domain")),
		5), #links
	(re.compile(r"<@!?(?P<id>\d+)>"),
		lambda contents, hit, message, out: message.guild.get_member(int(hit.group("id"))).display_name,
		1), # user
	(re.compile(r"<@&(?P<id>\d+)>"),
		lambda contents, hit, message, out: translations[settings[f"{message.guild.id}"].setdefault("lang", "en")]["role"].format(message.guild.get_role(int(hit.group("id"))).name),
		1), # role
	(re.compile(r"<a?:(?P<name>[^:]+):\d+>"),
		lambda contents, hit, message, out: hit.group("name"),
		1), # custom emote
	( re.compile(r"<#(?P<id>\d+)>"),
		lambda contents, hit, message, out: message.guild.get_channel(int(hit.group("id"))).name,
		1), # channel
]

async def sub_e(contents: str, message: discord.Message, pattern: re.Pattern, skip: int, substitutor) -> str:
	elements = list(pattern.finditer(contents))
	out = ""
	split = pattern.split(contents)
	while split:
		sentence = split.pop(0)
		if split:
			for i in range(skip):
				split.pop(0)
		out += sentence
		if elements:
			out += substitutor(contents, elements.pop(0), message, None) if isinstance(substitutor, Callable) else await substitutor(elements.pop(0))
	return out

async def prep_text(contents: str, message: discord.Message):
	for d in expressions:
		pattern, sub, skip = d
		contents = await sub_e(contents, message, pattern, skip, sub)
	return contents

time_out: Union[asyncio.Task, None] = None

@bot.event
async def on_message(message: discord.Message):
	global settings, sources, time_out, last_users
	try:
		context = await bot.get_context(message)
		if context.command is None:
			raise commands.CommandError
		await bot.invoke(context)
	except Exception as e:
		# if e is commands.ArgumentParsingError:
		gid = f"{message.guild.id}"
		if gid in settings and not message.author.bot and not settings[gid].setdefault("mode", "unrestricted") == "off":
			enabled = message.author.id in settings[gid]["whitelist"] if settings[gid]["mode"] == "whitelist" else message.author.id not in settings[gid]["usage_blacklist"] if settings[gid]["mode"] == "blacklist" else True
			if "channel" in settings[gid] and message.channel.id == settings[gid]["channel"] and enabled:
				if (message.author.voice.self_mute or settings[gid].setdefault("mute-optional", False)) and not list(filter(lambda member: member.id in settings[gid].setdefault("presence_blacklist", {}).setdefault("ids", []), message.author.voice.channel.members)):
					# noinspection PyTypeChecker
					vc: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=message.guild)
					if vc is None or vc.channel != message.author.voice.channel:
						if vc is not None and vc.is_connected():
							await vc.disconnect(force=True)
						channel = message.author.voice.channel
						await channel.connect()
					guild = message.guild
					text = message.content
					text = await prep_text(text, message)
					name = f"{gid}_{datetime.datetime.now().timestamp()}.mp3"
					tts = googleTTS(
						text=f"{message.author.display_name + ': ' if gid not in last_users or not last_users[gid] == message.author.id else ''}{text}", lang=settings[gid].setdefault("lang", "en"),
						slow=False
					)
					last_users[gid] = message.author.id
					tts.save(name)
					source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(name))
					if time_out:
						time_out.cancel()
						time_out = None
					sources.setdefault(gid, []).append(SourceWithExtra(message.author, name, source))
					if not guild.voice_client.is_playing():
						async def play_first():
							global sources, time_out

							def after(_):
								global sources
								os.remove(sources[gid].pop(0).file)
								bot.loop.create_task(play_first())
							if gid in sources and len(sources[gid]) != 0:
								guild.voice_client.play(sources[gid][0].source, after=after)
							else:
								async def stop():
									async def disconnect():
										await asyncio.sleep(300)
										await guild.voice_client.disconnect(force=True)

									async def forget():
										global last_users
										await asyncio.sleep(30)
										last_users[gid] = None
									await asyncio.gather(disconnect(), forget())
								time_out = bot.loop.create_task(stop())
						await play_first()


@bot.event
async def on_ready():
	logger.info(f"ready as {bot.user.name}")

def main():
	bot.run(os.getenv('BOT_TOKEN'))

if __name__ == '__main__':
	main()
