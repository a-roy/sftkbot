#!/usr/bin/env python3

import sys
import discord
from discord.ext import commands
import json
import sftklib
import sftkweb
import re
import time
from googleapiclient.errors import HttpError

description = "Information source for Street Fighter x Tekken"
bot = commands.Bot(command_prefix='!', description=description)
retry_time = 0
retry_increment = 300

def prep(token : str):
    return re.sub('\W+', '', token).lower()

@bot.event
async def on_ready():
    retry_time = 0
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command(aliases=["Frames"])
async def frames(ctx, char : str, move : commands.Greedy[str]):
    """Looks up frame data for a move."""
    await bot.type()
    if (len(move) == 0):
        move = [char]
        char = "#Misc Data#"
    fd = {}
    try:
        fd = sftklib.frames(char, ' '.join(move))
    except (BrokenPipeError, ConnectionAbortedError) as e:
        print(e, file=sys.stderr)
        await ctx.send('Failed to retrieve data.')
    except HttpError as e:
        await ctx.send('Character not found: **{0}**'.format(char))
    except Exception as e:
        print(type(e), file=sys.stderr)
        print(e, file=sys.stderr)
        await ctx.send('An error has occurred.')
    else:
        embed = discord.Embed(
                title='{0}'.format(char.title()))
        c = prep(char)
        if c == 'bison': c = 'mbison'
        if c in sftkweb.pics:
            embed.set_thumbnail(url=sftkweb.pics[c])
        if not fd:
            embed.description = 'Move not found.'
        for k, v in fd.items():
            embed.add_field(name=k, value=v)
        await ctx.send(embed=embed)

@bot.command(aliases=["Partner"])
async def partner(ctx, *, char):
    """Suggests potential partners for a character."""
    c = prep(char)
    if c == 'bison': c = 'mbison'
    await ctx.send(sftklib.partner(c))

@bot.command(aliases=["Combo", "combos", "Combos"])
async def combo(ctx, char, tags : commands.Greedy[str]):
    """Looks up combos for a character."""
    c = prep(char)
    if c == 'bison': c = 'mbison'
    try:
        message, details, postmessage = sftklib.search(c, tags)
    except FileNotFoundError:
        await ctx.send('Character not available: **{0}**'.format(c))
    else:
        embed = discord.Embed(
                title='{0} combos'.format(c.capitalize()),
                description=message)
        if c in sftkweb.pics:
            embed.set_thumbnail(url=sftkweb.pics[c])
        for k, v in details.items():
            embed.add_field(name=k, value=v)
        if postmessage != "":
            embed.add_field(name="Enders", value=postmessage)
        await ctx.send(embed=embed)

@bot.command(aliases=["Synergy"])
async def synergy(ctx, *args):
    """Summarizes partner considerations for a character."""
    char = args[0]
    extra = args[1:]
    section = None
    detail = None
    if len(extra) >= 1:
        section = prep(extra[0])
        if len(extra) >= 2:
            detail = prep(extra[1])
    c = prep(char)
    if c == 'bison': c = 'mbison'
    try:
        message, details = sftklib.synergy(c, section, detail)
    except:
        await bot.say('Character not available: **{0}**'.format(c))
    else:
        embed = discord.Embed(
                title='{0} synergy'.format(c.capitalize()),
                description=message)
        if c in sftkweb.pics:
            embed.set_thumbnail(url=sftkweb.pics[c])
        for k, v in details.items():
            embed.add_field(name=k, value=v)
        await ctx.send(embed=embed)

@bot.command(aliases=["Sanford"])
async def sanford(ctx):
    """Pick a top tier!"""
    await ctx.send("https://www.youtube.com/watch?v=sGh4ZU4H5Hk")

@bot.command(aliases=["Desmond"])
async def desmond(ctx):
    """Only broken games are good!"""
    await ctx.send("https://www.youtube.com/watch?v=_jyPQaHftWk")

@bot.command(aliases=["Tiers", "tier", "tierlist"])
async def tiers(ctx):
    await ctx.send(sftklib.tiers())

if __name__ == '__main__':
    api_token = ''
    with open('SFTKBot-discord.json') as f:
        j = json.load(f)
        api_token = j['api_token']
    while api_token:
        try:
            bot.run(api_token)
            break
        except (ConnectionResetError, RuntimeError, OSError) as e:
            bot.close()
            time.sleep(retry_time)
            retry_time += retry_increment
        except:
            bot.close()
            break
