import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import sqlite3
import datetime
import shortuuid as shortuuid
from apiclient import discovery
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd
import pickle
import asyncio

guildinfosql = r'database\guildinfosql.db'
conn = sqlite3.connect(guildinfosql)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
intents.members = True
intents.bans = True
bot = commands.Bot(command_prefix="%", intents=intents)

bantypelist = ["Harassing", "Spamming", "Raiding", "Racist content", "Disturbing content", "Alts", "Bots",
               "Other Unwanted Content", "Loli content", "Real child pornography content",
               "Sexual advances with minors", "Unwanted NSFW", "Other Sexual Content", "Piracy", "Viruses",
               "Selling drugs", "Under 18", "Under 13", "Other illegal Content"]

imagechannel = bot.get_channel(int(834577801449046046))
verificationchannel = bot.get_channel(int(834577801449046046))

botadmins = []
theautobanlist = []
modchannels = []
runningmodchannels = []


async def updateglogs():
    while True:
        guildinfo = conn.cursor()
        sqlcommand = "SELECT * FROM reportList WHERE certified=1"
        guildinfo.execute(sqlcommand)
        recordset = guildinfo.fetchall()

        columns = [col[0] for col in guildinfo.description]
        df = pd.DataFrame(recordset, columns=columns)
        if os.path.exists('bandatabase.csv'):
            os.remove('bandatabase.csv')
        df.to_csv(r'bandatabase.csv', index=False)
        guildinfo.close()

        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        drive = GoogleDrive(gauth)

        scopes = ['https://www.googleapis.com/auth/drive']
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', scopes, )
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        DRIVE = discovery.build('drive', 'v2', credentials=creds)
        ufile = os.path.basename('bandatabase.csv')
        f = drive.CreateFile({'title': ufile})
        f.SetContentFile('bandatabase.csv')
        f.Upload()
        metadata = {'title': ufile,
                    "parents": [{"id": '15_KzIzvqfffgr0Z_2PWubDUqrCJBRPCS', "kind": "drive#childList"}]}
        res = DRIVE.files().insert(convert=False, body=metadata,
                                   media_body='bandatabase.csv', fields='mimeType,exportLinks,id').execute()

        with open('curdata.txt', 'w', encoding='utf-8') as w:
            w.write(str('https://docs.google.com/spreadsheets/d/' + res.get('id')))

        await asyncio.sleep(43200)


async def fetch_modchan(guild):
    guildinfo = conn.cursor()
    guildinfo.execute("SELECT * FROM guildsInfo")
    rows = guildinfo.fetchall()
    for row in rows:
        if row[1] == guild.id:
            return bot.get_channel(row[2])
    guildinfo.close()


async def banlistupdate(member):
    embed = discord.Embed(title='Ban database update')
    embed = await membersearch(embed, member)
    for guild in bot.guilds:
        modchan = await fetch_modchan(guild)
        if modchan is not None:
            await modchan.send("Ban database update for " + str(member), embed=embed)


async def verifyban(embed, member):
    global verificationchannel
    embed_dict = embed.to_dict()
    embed_dict['color'] = 0xe74c3c
    embed = discord.Embed.from_dict(embed_dict)
    reacto = await verificationchannel.send("Verification needed for " + str(member), embed=embed)
    await reacto.add_reaction('✅')
    await reacto.add_reaction('❌')


async def membersearch(embed, member):
    guildinfo = conn.cursor()
    sqlcommand = "SELECT * FROM reportList WHERE reportedUserID=? AND certified=1"
    guildinfo.execute(sqlcommand, (member.id,))
    rows = guildinfo.fetchall()
    reports = ""
    usernote = "None"
    for row in rows:
        usernote = str(row[11])
        guildname = bot.get_guild(row[3]).name
        reports += ("Server: " + str(guildname) + "\n" + "Ban reason: " + str(row[4]) + "\n" + "Evidence: " + row[
            5] + "\n" + "Ban Type: "
                    + str(row[6]) + "\n" + "Ban Notes: " + row[7] + "\n" + "Time of Ban: " + str(
                    row[8]) + "\n" + "Ban ID: " + str(row[10]) + "\n" + "\n")
    embed.add_field(name='Member', value=str(member) + " - " + str(member.id), inline=True)
    embed.add_field(name='Created at', value=str(member.created_at)[:-7], inline=True)
    embed.add_field(name='User notes', value=usernote, inline=False)
    if reports != "":
        embed.add_field(name='Reports for member', value=reports, inline=False)
    else:
        embed.add_field(name='Reports for member', value='Member has no reports', inline=False)
    embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/708059652633526374.png', text=("Report info " + str(
        datetime.datetime.now())[:-7]))
    guildinfo.close()
    return embed


async def usersearch(embed, user):
    guildinfo = conn.cursor()
    sqlcommand = "SELECT * FROM reportList WHERE reportedUserID=? AND certified=1"
    guildinfo.execute(sqlcommand, (user.id,))
    rows = guildinfo.fetchall()
    reports = ""
    usernote = "None"
    for row in rows:
        usernote = str(row[11])
        guildname = bot.get_guild(row[3]).name
        reports += ("Server: " + str(guildname) + "\n" + "Ban reason: " + str(row[4]) + "\n" + "Evidence: " + row[
            5] + "\n" + "Ban Type: "
                    + str(row[6]) + "\n" + "Ban Notes: " + row[7] + "\n" + "Time of Ban: " + str(
                    row[8]) + "\n" + "Ban ID: " + str(row[10]) + "\n" + "\n")
    embed.add_field(name='User', value=str(user) + " - " + str(user.id), inline=True)
    embed.add_field(name='User notes', value=usernote, inline=False)
    if reports != "":
        embed.add_field(name='Reports for user', value=reports, inline=False)
    else:
        embed.add_field(name='Reports for user', value='User has no reports', inline=False)
    embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/708059652633526374.png', text=("Report info " + str(
        datetime.datetime.now())[:-7]))
    guildinfo.close()
    return embed


@bot.command()
async def dataupdate(ctx):
    if ctx.author.id != 415158701331185673:
        return
    await updateglogs()


@bot.command()
async def remove(ctx, arg):
    if ctx.channel != verificationchannel:
        return
    if ctx.author.id not in botadmins:
        return
    guildinfo = conn.cursor()
    try:
        guildinfo.execute("UPDATE reportList SET certified=? WHERE banID=?", (int(2), str(arg)))
    except Exception as e:
        print(e)
        await ctx.channel.send("Ban ID not found")
        guildinfo.close()
        return
    await ctx.channel.send("Ban removal successful")
    conn.commit()
    guildinfo.close()


@bot.command()
async def note(ctx, arg, *args):
    if ctx.channel != verificationchannel:
        return
    if ctx.author.id not in botadmins:
        return
    noted = (" ".join(args[:])).strip()
    guildinfo = conn.cursor()
    try:
        guildinfo.execute("UPDATE reportList SET userNotes=? WHERE reportedUserID=?", (str(noted), int(arg)))
    except Exception as e:
        print(e)
        await ctx.channel.send("User ID not found")
        guildinfo.close()
        return
    await ctx.channel.send("User note successful")
    conn.commit()
    guildinfo.close()


@bot.command()
async def communityban(ctx, arg, *args):
    if ctx.channel != verificationchannel:
        return
    if ctx.author.id not in botadmins:
        return
    reason = (" ".join(args[:])).strip()
    print(reason)
    if reason == "" or reason == " ":
        await ctx.channel.send("Please input a reason")
        return
    user = await bot.fetch_user(int(arg))
    if user is None:
        await ctx.channel.send("User ID could not be found")
        return
    guildinfo = conn.cursor()
    guildinfo.execute("UPDATE reportList SET autoBan=1, autoBanReason=? WHERE reportedUserID=?", (reason, user.id))
    conn.commit()
    guildinfo.execute("SELECT * FROM guildsInfo WHERE autoBan=1")
    rows = guildinfo.fetchall()
    theautobanlist.append(user.id)
    guildinfo.close()
    for row in rows:
        guild = bot.get_guild(int(row[1]))
        modchan = await fetch_modchan(guild)
        await guild.ban(user=user, reason=str(reason))
        await modchan.send("Community Ban: " + str(user) + " - " + str(user.id) + " for " + reason)


@bot.command()
@commands.has_permissions(ban_members=True)
async def autobanlist(ctx):
    guildinfo = conn.cursor()
    guildinfo.execute("SELECT * FROM reportList WHERE autoBan=1")
    rows = guildinfo.fetchall()
    embed = discord.Embed(title='Auto ban list', colour=0x000000)
    banlist = ""
    for row in rows:
        user = await bot.fetch_user(row[1])
        banlist += (str(user) + " - " + str(row[1]) + "\n" + "Reason: " + str(row[13]) + "\n" + "\n")
    embed.add_field(name="Users", value=banlist)
    embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/708059652633526374.png',
                     text=(str(datetime.datetime.now())[:-7]))
    guildinfo.close()
    await ctx.channel.send(embed=embed)


@bot.event
async def on_ready():
    global imagechannel, verificationchannel, theautobanlist
    guildinfo = conn.cursor()
    print(f'{bot.user} has connected to Discord!')
    for guild in bot.guilds:
        print(f'Connected to {guild.name}')
    guildinfo.execute("SELECT * FROM guildsInfo")
    rows = guildinfo.fetchall()
    modchannels.clear()
    runningmodchannels.clear()
    for row in rows:
        modchannels.append(bot.get_channel(row[2]))
        runningmodchannels.append(0)
    print(modchannels)
    print(runningmodchannels)
    imagechannel = bot.get_channel(int(834577801449046046))
    verificationchannel = bot.get_channel(int(834726338182512682))
    await bot.change_presence(activity=discord.Game(name="Run %setmodchannel to setup the bot"))
    guildinfo.execute("SELECT * FROM reportList WHERE autoBan=1")
    rows = guildinfo.fetchall()
    for row in rows:
        theautobanlist.append(int(row[1]))
    someinfo = await bot.application_info()
    for member in someinfo.team.members:
        botadmins.append(member.id)
    guildinfo.close()


@bot.event
async def on_member_ban(guild, user):
    print("removed")
    modchannel = await fetch_modchan(guild)
    if modchannel is None:
        return
    logs = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()
    logs = logs[0]
    if logs.user == bot.user:
        return
    banid = shortuuid.ShortUUID().random(length=22)
    embed = discord.Embed(title='Report', colour=0xe74c3c)
    embed.add_field(name='Banned User', value=str(user) + " - " + str(user.id), inline=True)
    embed.add_field(name='Server', value=guild.name + " - " + str(guild.id), inline=True)
    embed.add_field(name='Reason', value=logs.reason, inline=False)
    embed.add_field(name='Evidence', value="None", inline=False)
    embed.add_field(name='Ban Type', value="None", inline=False)
    embed.add_field(name='Ban Notes', value="None", inline=False)
    embed.add_field(name='Ban ID', value=str(banid))
    embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/708059652633526374.png', text=("Report " + str(
        datetime.datetime.now())[:-7]))
    reacto = await modchannel.send(content="I see you just banned " + str(user) + """
To help us categorize this ban, please do the following:
Press 🔨 to change ban reason if necessary.
Press 📷 to add images or links to the evidence.
Press #️⃣ to select the ban type.
Press 🗒️ to add ban notes.
Press ✅ to submit the ban to the database.
You can press ❌ to cancel.""", embed=embed)
    await reacto.add_reaction('🔨')
    await reacto.add_reaction('📷')
    await reacto.add_reaction('#️⃣')
    await reacto.add_reaction('🗒️')
    await reacto.add_reaction('✅')
    await reacto.add_reaction('❌')


bot.remove_command('help')


@bot.command()
async def help(ctx):
    await ctx.channel.send("""List of commands:
`%setmodchannel` - sets the bot's output to the current channel
`%report userid` - creates an editable report ticket for the user
`%info userid` - returns info about the reports the user has
`%data` - provides a link to the full database of individuals on the ban list
`%autobanlist` - retrieves the list of users on the auto ban list
`%autoban` - toggle to enable the bot to auto ban users on the auto ban list (only used in extreme circumstances)""")


@bot.command()
@commands.has_permissions(ban_members=True)
async def data(ctx):
    with open('curdata.txt', 'r', encoding='utf-8') as w:
        datatosend = w.read()
    await ctx.message.reply(datatosend, mention_author=False)


@bot.command()
@commands.has_permissions(administrator=True)
async def setmodchannel(ctx):
    print(f'Connected to {ctx.guild.name}')
    guildinfo = conn.cursor()
    sqlcommand = """DELETE FROM guildsInfo WHERE guildID=?"""
    try:
        guildinfo.execute(sqlcommand, (ctx.guild.id,))
        conn.commit()
    except:
        print("expected fail")
    sqlcommand = """INSERT INTO guildsInfo (guildName,guildID,modChannelID,autoBan) Values(?,?,?,?)"""
    guildinfo.execute(sqlcommand, (ctx.guild.name, ctx.guild.id, ctx.channel.id, int(0)))
    conn.commit()
    guildinfo.execute("SELECT * FROM guildsInfo")
    rows = guildinfo.fetchall()
    modchannels.clear()
    runningmodchannels.clear()
    for row in rows:
        modchannels.append(bot.get_channel(row[2]))
        runningmodchannels.append(0)
    await ctx.channel.send("Set channel to " + str(ctx.channel))
    guildinfo.close()


@bot.command()
@commands.has_permissions(administrator=True)
async def autoban(ctx):
    modchannel = await fetch_modchan(ctx.guild)
    if modchannel is None:
        return
    guildinfo = conn.cursor()
    guildinfo.execute("SELECT * FROM guildsInfo WHERE guildID=?", (int(ctx.guild.id),))
    rows = guildinfo.fetchall()
    for row in rows:
        if row[3] == 0:
            guildinfo.execute("SELECT * FROM reportList WHERE autoBan=1")
            rows2 = guildinfo.fetchall()
            abanlist = []

            def check(m):
                return m.author.id == ctx.author.id and m.channel == ctx.channel

            for line in rows2:
                abanlist.append(line[1])
            for member in ctx.guild.members:
                if member.id in abanlist:
                    await ctx.channel.send("Warning: " + member + " will be banned if you enable the auto ban list")
            await ctx.channel.send("Enabling this will allow the bot to auto ban individuals with heinous "
                                   "offences\nDo you want to continue?")
            msg = await bot.wait_for("message", check=check, timeout=120)
            if msg.content.lower() == "y" or msg.content.lower() == "yes":
                for row2 in rows2:
                    banuser = await bot.fetch_user(row2[1])
                    await ctx.guild.ban(user=banuser, reason=str(row2[13]))
                guildinfo.execute("UPDATE guildsInfo SET autoBan=1 WHERE guildID=?", (int(ctx.guild.id),))
                await ctx.channel.send("Autoban list turned on")
                conn.commit()
                guildinfo.close()
                return
            else:
                await ctx.channel.send("Autoban list turned off")
                guildinfo.close()
                return
        elif row[3] == 1:
            guildinfo.execute("UPDATE guildsInfo SET autoBan=0 WHERE guildID=?", (int(ctx.guild.id),))
            await ctx.channel.send("Autoban list turned off")
            conn.commit()
            guildinfo.close()
            return


@bot.command()
@commands.has_permissions(ban_members=True)
async def report(ctx):
    modchannel = await fetch_modchan(ctx.guild)
    if modchannel is None:
        ctx.channel.send("You need to set the mod channel with %setmodchannel to use that")
        return
    if str(ctx.message.content).lower().strip() == "%report":
        await ctx.channel.send("Use `%report userid` to file a report for a user")
        return
    else:
        messageline = ctx.message.content[7:].strip()
        messageline = messageline.replace("<", "")
        messageline = messageline.replace("@", "")
        messageline = messageline.replace("!", "")
        messageline = messageline.replace(">", "")
        try:
            userid = int(messageline)
            user = bot.get_user(userid)
            if user is None:
                await ctx.channel.send("Invalid User ID")
                return
            banid = shortuuid.ShortUUID().random(length=22)
            embed = discord.Embed(title='Report', colour=0xe74c3c)
            embed.add_field(name='Banned User', value=str(user) + " - " + str(user.id), inline=True)
            embed.add_field(name='Server', value=ctx.guild.name + " - " + str(ctx.guild.id), inline=True)
            embed.add_field(name='Reason', value="None", inline=False)
            embed.add_field(name='Evidence', value="None", inline=False)
            embed.add_field(name='Ban Type', value="None", inline=False)
            embed.add_field(name='Ban Notes', value="None", inline=False)
            embed.add_field(name='Ban ID', value=str(banid))
            embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/708059652633526374.png', text=("Report " + str(
                datetime.datetime.now())[:-7]))
            reacto = await modchannel.send(content="I see you just reported " + str(user) + """
To help us categorize this ban, please do the following:
Press 🔨 to change ban reason if necessary.
Press 📷 to add images or links to the evidence.
Press #️⃣ to select the ban type.
Press 🗒️ to add ban notes.
Press ✅ to submit the ban to the database.
You can press ❌ to cancel.""", embed=embed)
            await reacto.add_reaction('🔨')
            await reacto.add_reaction('📷')
            await reacto.add_reaction('#️⃣')
            await reacto.add_reaction('🗒️')
            await reacto.add_reaction('✅')
            await reacto.add_reaction('❌')
        except:
            await ctx.channel.send("Invalid User ID")
            return


@bot.command()
@commands.has_permissions(ban_members=True)
async def info(ctx, arg):
    print("recieved")
    try:
        if ctx.message.content[5:].strip().startswith('<'):
            arg = ctx.message.content[5:].strip().replace("<", "")
            arg = arg.replace("@", "")
            arg = arg.replace("!", "")
            arg = arg.replace(">", "")
        int(arg)
        print("success")
        # dumb code, fix later
        try:
            try:
                member = ctx.guild.get_member(int(arg))
                embed = discord.Embed(title='Member Info', color=0xfffffe)
                embed = await membersearch(embed, member)
            except:

                user = await bot.fetch_user(int(arg))
                embed = discord.Embed(title='User Info', color=0xfffffe)
                embed = await usersearch(embed, user)
        except:
            await ctx.channel.send("Invalid User ID")
            return
        reacto = await ctx.channel.send(embed=embed)
        if ctx.channel in modchannels or ctx.channel == verificationchannel:
            await reacto.add_reaction('✅')
            await reacto.add_reaction('❌')
            await reacto.add_reaction('☠')
    except:
        print("fail??")
        await ctx.channel.send("Invalid User ID")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    channel = bot.get_channel(payload.channel_id)
    if channel not in modchannels and channel != verificationchannel:
        return
    guild = bot.get_guild(payload.guild_id)
    user = guild.get_member(payload.user_id)
    if user == bot.user:
        return
    message = await channel.fetch_message(payload.message_id)

    def check(m):
        return m.author.id == user.id and m.channel == channel

    def check2(m):
        try:
            int(m.content)
        except:
            return False
        return 0 < int(m.content) < 20

    if message.author == bot.user:
        await message.remove_reaction(payload.emoji, user)
        try:
            newEmbed = message.embeds[0]
            embed_dict = newEmbed.to_dict()
        except:
            return
        if embed_dict['color'] == 0x00FF00 or embed_dict['color'] == 0x000000:
            return
        if channel == verificationchannel:
            guildinfo = conn.cursor()
            if payload.emoji.name == '✅':
                embed_dict['color'] = 0x00FF00
                newEmbed = discord.Embed.from_dict(embed_dict)
                reported = newEmbed.fields[0].value.split()
                banid = newEmbed.fields[6].value
                await message.edit(embed=newEmbed)
                try:
                    guildinfo.execute("UPDATE reportList SET certified=? WHERE banID=?", (int(1), str(banid)))
                except Exception as e:
                    print(e)
                    print("major error, kill")
                conn.commit()
                await banlistupdate(bot.get_user(int(reported[-1])))
            elif payload.emoji.name == '❌':
                embed_dict['color'] = 0x000000
                newEmbed = discord.Embed.from_dict(embed_dict)
                banid = newEmbed.fields[6].value
                await message.edit(embed=newEmbed)
                try:
                    guildinfo.execute("UPDATE reportList SET certified=? WHERE banID=?", (int(2), str(banid)))
                except Exception as e:
                    print(e)
                    print("major error, kill")
                conn.commit()
            guildinfo.close()
        else:
            if not user.guild_permissions.ban_members:
                await channel.send(user.name + " you do not have permission to perform that action")
                return
            if newEmbed.fields[0].name == "Banned User":
                if embed_dict['color'] == 0xe74c3b:
                    runningmodchannels[modchannels.index(channel)] = 0
                    embed_dict['color'] = 0xe74c3c
                elif embed_dict['color'] == 0xf1c40e:
                    embed_dict['color'] = 0xf1c40f
                    runningmodchannels[modchannels.index(channel)] = 0
                if payload.emoji.name == '✅':
                    if embed_dict['color'] == 0xf1c40f:
                        embed_dict['color'] = 0x00FF00
                        newEmbed = discord.Embed.from_dict(embed_dict)
                        reported = newEmbed.fields[0].value.split()
                        reason = newEmbed.fields[2].value
                        evidence = newEmbed.fields[3].value
                        bantype = newEmbed.fields[4].value
                        bannotes = newEmbed.fields[5].value
                        banid = newEmbed.fields[6].value
                        reportname = ' '.join(reported[:-2])
                        if reason == "Loli content" or reason == "Real child pornography content":
                            evidence = "[Evidence removed due to sensitive content]"
                        await message.edit(embed=newEmbed)
                        guildinfo = conn.cursor()
                        sql = """INSERT INTO reportList (reportedUserName,reportedUserID,guildName,guildID,reason,
                        evidence,banType,banNotes,time, certified, banID, userNotes, autoBan, autoBanReason) 
                        Values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
                        try:
                            guildinfo.execute(sql, (
                                "Removed for GDPR", int(reported[-1]), "Removed for GDPR", int(guild.id), reason, evidence,
                                bantype,
                                bannotes, str(datetime.datetime.now())[:-7], int(0), banid, "None", int(0), "None"))
                        except Exception as e:
                            print(e)
                            print("major error, kill")
                        conn.commit()
                        guildinfo.close()
                        await verifyban(newEmbed, await bot.fetch_user(int(reported[-1])))
                    else:
                        await channel.send("Please enter the ban type and ban reason before submitting")
                elif payload.emoji.name == '🔨':
                    mesg = await channel.send('Enter a new ban reason')
                    try:
                        msg = await bot.wait_for("message", check=check, timeout=120)
                    except TimeoutError:
                        await mesg.delete()
                        return
                    await mesg.delete()
                    if newEmbed.fields[4].value != "None":
                        embed_dict['color'] = 0xf1c40f
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    newEmbed.set_field_at(2, name='Reason', value=msg.content, inline=False)
                    await message.edit(embed=newEmbed)
                elif payload.emoji.name == '📷':
                    runningmodchannels[modchannels.index(channel)] = 1
                    mesg = await channel.send('Provide evidence for ban')
                    if embed_dict['color'] == 0xf1c40f:
                        embed_dict['color'] = 0xf1c40e
                    else:
                        embed_dict['color'] = 0xe74c3b
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    await message.edit(embed=newEmbed)
                    embed_dict = newEmbed.to_dict()
                    while True:
                        # it works, needs changes to download messages and then upload to ensure they are saved
                        # might have some bug somewhere, haven't checked yet, but it doesn't impact the user
                        try:
                            msg = await bot.wait_for("message", check=check, timeout=1)
                            tosend = ""
                            for attachment in msg.attachments:
                                msg2 = await imagechannel.send(content=attachment.url)
                                if len(msg.attachments) > 1:
                                    tosend += msg2.content + "\n"
                                tosend += msg2.content
                            newEmbed = discord.Embed.from_dict(embed_dict)
                            if msg.content != "":
                                msg.content += "\n"
                            if newEmbed.fields[3].value == "None":
                                newEmbed.set_field_at(3, name='Evidence', value=msg.content + tosend, inline=False)
                            else:
                                newEmbed.set_field_at(3, name='Evidence',
                                                      value=newEmbed.fields[3].value + "\n" + msg.content + tosend,
                                                      inline=False)
                            await message.edit(embed=newEmbed)
                        except:
                            if runningmodchannels[modchannels.index(channel)] == 0:
                                break
                    await mesg.delete()

                elif payload.emoji.name == '#️⃣':
                    mesg = await channel.send("""Enter the ban type:
1 - Harassing
2 - Spamming
3 - Raiding
4 - Racist content
5 - Disturbing content
6 - Alts
7 - Bots
8 - Other Unwanted Content
9 - Loli content
10 - Real child pornography content
11 - Sexual advances with minors
12 - Unwanted NSFW
13 - Other Sexual Content
14 - Piracy
15 - Viruses
16 - Selling drugs
17 - Under 18
18 - Under 13
19 - Other illegal Content""")
                    try:
                        msg = await bot.wait_for("message", check=check2, timeout=60)
                    except TimeoutError:
                        await mesg.delete()
                        return
                    await mesg.delete()
                    if newEmbed.fields[2].value != "None":
                        embed_dict['color'] = 0xf1c40f
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    newEmbed.set_field_at(4, name='Ban Type', value=bantypelist[int(msg.content) - 1], inline=False)
                    await message.edit(embed=newEmbed)
                elif payload.emoji.name == '🗒️':
                    mesg = await channel.send('Enter ban notes')
                    try:
                        msg = await bot.wait_for("message", check=check, timeout=120)
                    except TimeoutError:
                        await mesg.delete()
                        return
                    await mesg.delete()
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    newEmbed.set_field_at(5, name='Ban Notes', value=msg.content, inline=False)
                    await message.edit(embed=newEmbed)
                elif payload.emoji.name == '❌':
                    embed_dict['color'] = 0x000000
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    await message.edit(embed=newEmbed)
            elif newEmbed.fields[0].name == "Member" or newEmbed.fields[0].name == "User":
                if payload.emoji.name == '✅':
                    embed_dict['color'] = 0x00FF00
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    await message.edit(embed=newEmbed)
                elif payload.emoji.name == '❌':
                    embed_dict['color'] = 0x000000
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    user2 = bot.get_user(int(newEmbed.fields[0].value.split()[2]))
                    try:
                        await guild.kick(user=user2, reason="Failed verification")
                    except PermissionError:
                        await channel.send("I don't have permissions to ban that user")
                    await message.edit(embed=newEmbed)
                    await channel.send(str(user2) + " was kicked from the server.")
                elif payload.emoji.name == '☠':
                    embed_dict['color'] = 0x000000
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    user2 = bot.get_user(int(newEmbed.fields[0].value.split()[2]))
                    try:
                        await guild.ban(user=user2, reason="Failed verification")
                    except PermissionError:
                        await channel.send("I don't have permissions to ban that user")
                    await message.edit(embed=newEmbed)
                    await channel.send(str(user2) + " was banned from the server.")


@bot.event
async def on_member_join(member):
    modchannel = await fetch_modchan(member.guild)
    if modchannel is None:
        return
    if member.id in theautobanlist:
        guildinfo = conn.cursor()
        guildinfo.execute("SELECT * FROM reportList WHERE reportedUserID=?", member.id)
        rows = guildinfo.fetchall()
        reason = ""
        for row in rows:
            reason = str(row[13])
        await member.guild.ban(user=member, reason="Auto community ban")
        await modchannel.send("Community Ban: " + str(member) + " - " + str(member.id) + " for " + reason)
        guildinfo.close()
    embed = discord.Embed(title='New member joined', color=0xfffffe)
    embed = await membersearch(embed, member)
    reacto = await modchannel.send(embed=embed)
    await reacto.add_reaction('✅')
    await reacto.add_reaction('❌')
    await reacto.add_reaction('☠')


bot.run(TOKEN)
