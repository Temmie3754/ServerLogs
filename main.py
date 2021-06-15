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
from discord.ext.commands import MissingPermissions
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_permission
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType


guildinfosql = r'database\guildinfosql.db'
conn = sqlite3.connect(guildinfosql)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
intents.members = True
intents.bans = True
bot = commands.Bot(command_prefix="£", intents=intents)
slash = SlashCommand(bot, sync_commands=True)

bantypelist = ["Harassing", "Spamming", "Raiding", "Racist content", "Disturbing content", "Alts", "Bots",
               "Other Unwanted Content", "Loli content", "Real child pornography content",
               "Sexual advances with minors", "Unwanted NSFW", "Other Sexual Content", "Piracy", "Viruses",
               "Selling drugs", "Under 18", "Under 13", "Other"]

imagechannel = bot.get_channel(int(834577801449046046))
verificationchannel = bot.get_channel(int(834577801449046046))
botadminguild = 834418606279884801
botadminrole = 836144387099721729

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
        for i in range(len(recordset)):
            row = list(recordset[i])
            row[0] = await bot.fetch_user(row[1])
            recordset[i] = tuple(row)
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
    embed = discord.Embed(title='Ban database update', color=0xFFFFFE)
    embed = await membersearch(embed, member)
    guildinfo = conn.cursor()
    guildinfo.execute("SELECT * FROM guildsInfo WHERE updates=1")
    rows = guildinfo.fetchall()
    guildsupdate = []
    for row in rows:
        guildsupdate.append(row[1])
    for guild in bot.guilds:
        if guild.id not in guildsupdate:
            return
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


guild_ids = []


@bot.event
async def on_ready():
    global imagechannel, verificationchannel, theautobanlist, guild_ids
    guildinfo = conn.cursor()
    print(f'{bot.user} has connected to Discord!')

    for guild in bot.guilds:
        print(f'Connected to {guild.name}')
        guild_ids.append(guild.id)
    print(guild_ids)
    DiscordComponents(bot)
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


@bot.command()
async def dataupdate(ctx):
    if ctx.author.id != 415158701331185673:
        print("death")
        return
    await updateglogs()


@slash.slash(name='remove', description='Removes a ban from the database', guild_ids=[botadminguild],
             options=[
               create_option(
                 name="banid",
                 description="ID of the ban to remove",
                 option_type=3,
                 required=True
               )])
@slash.permission(guild_id=botadminguild, permissions=[create_permission(botadminrole, SlashCommandPermissionType.ROLE, True)])
async def _remove(ctx, banid):
    if ctx.author.id not in botadmins:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    if ctx.channel != verificationchannel:
        await ctx.send("Please do the command in the verification channel", hidden=True)
        return
    await ctx.defer()
    guildinfo = conn.cursor()
    try:
        guildinfo.execute("UPDATE reportList SET certified=? WHERE banID=?", (int(2), str(banid)))
    except Exception as e:
        print(e)
        await ctx.send("Ban ID not found")
        guildinfo.close()
        return
    await ctx.send("Ban removal successful")
    conn.commit()
    guildinfo.close()


@slash.slash(name='alt', description='Links an alt account to have the same record as the main account', guild_ids=[botadminguild],
             options=[
               create_option(
                 name="userid1",
                 description="ID of first account",
                 option_type=3,
                 required=True
               ),
               create_option(
                 name="userid2",
                 description="ID of second account",
                 option_type=3,
                 required=True
               )
             ])
@slash.permission(guild_id=botadminguild, permissions=[create_permission(botadminrole, SlashCommandPermissionType.ROLE, True)])
async def _alt(ctx, userid1, userid2):
    if ctx.author.id not in botadmins:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    if ctx.channel != verificationchannel:
        await ctx.send("Please do the command in the verification channel", hidden=True)
        return
    try:
        userid1 = int(userid1)
        userid2 = int(userid2)
    except:
        await ctx.send("Incorrect User ID", hidden=True)
        return
    try:
        username1 = await bot.fetch_user(userid1)
        username2 = await bot.fetch_user(userid2)
    except discord.NotFound:
        await ctx.send("Incorrect user ID", hidden=True)
        return
    await ctx.defer()
    guildinfo = conn.cursor()
    sqlcommand = "SELECT * FROM reportList WHERE reportedUserID=? AND certified=1"
    guildinfo.execute(sqlcommand, (userid1,))
    user1bans = guildinfo.fetchall()
    guildinfo.execute(sqlcommand, (userid2,))
    user2bans = guildinfo.fetchall()

    if len(user1bans) != 0:
        notetodo = "Alt of " + str(username1) + " - " + str(userid1)
        for row in user1bans:
            if row[11] != "None":
                notetodo = row[11] + "\n" + notetodo
            sql = """INSERT INTO reportList (reportedUserName,reportedUserID,guildName,guildID,reason,
                                    evidence,banType,banNotes,time, certified, banID, userNotes, autoBan, autoBanReason) 
                                    Values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            guildinfo.execute(sql, ("PII removed", int(userid2), "PII removed", int(row[3]), row[4], row[5], row[6],
                                    row[7], row[8], row[9], shortuuid.ShortUUID().random(length=22), notetodo, row[12], row[13]))
            notetodo = "Alt of " + str(username2) + " - " + str(userid2)
            guildinfo.execute("UPDATE reportList SET userNotes=? WHERE reportedUserID=?", (notetodo, userid1))
    if len(user2bans) != 0:
        notetodo = "Alt of " + str(username2) + " - " + str(userid2)
        for row in user2bans:
            if row[11] != "None":
                notetodo = row[11] + "\n" + notetodo
            sql = """INSERT INTO reportList (reportedUserName,reportedUserID,guildName,guildID,reason,
                                    evidence,banType,banNotes,time, certified, banID, userNotes, autoBan, autoBanReason) 
                                    Values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            guildinfo.execute(sql, ("PII removed", int(userid1), "PII removed", int(row[3]), row[4], row[5], row[6],
                                    row[7], row[8], row[9], shortuuid.ShortUUID().random(length=22), notetodo, row[12], row[13]))
            notetodo = "Alt of " + str(username1) + " - " + str(userid1)
            guildinfo.execute("UPDATE reportList SET userNotes=? WHERE reportedUserID=?", (notetodo, userid2))
    if len(user1bans) == 0 and len(user2bans) == 0:
        await ctx.send("Could not find any bans on record for these users, did you enter the IDs incorrectly?")
    else:
        conn.commit()
        guildinfo.close()
        await ctx.send("Alt update successful")


@slash.slash(name='note', description='Adds a note to the user', guild_ids=[botadminguild],
             options=[
               create_option(
                 name="userid",
                 description="ID of the user",
                 option_type=3,
                 required=True
               ),
               create_option(
                 name="note",
                 description="The note for the user",
                 option_type=3,
                 required=True
               )
             ])
@slash.permission(guild_id=botadminguild, permissions=[create_permission(botadminrole, SlashCommandPermissionType.ROLE, True)])
async def _note(ctx, userid, note):
    if ctx.author.id not in botadmins:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    if ctx.channel != verificationchannel:
        await ctx.send("Please do the command in the verification channel", hidden=True)
        return
    await ctx.defer()
    noted = note
    print(note)
    guildinfo = conn.cursor()
    try:
        guildinfo.execute("UPDATE reportList SET userNotes=? WHERE reportedUserID=?", (str(noted), int(userid)))
    except Exception as e:
        print(e)
        await ctx.send("User ID not found")
        guildinfo.close()
        return
    await ctx.send("User note successful")
    conn.commit()
    guildinfo.close()


@slash.slash(name='communityban', description='Adds a user to the community auto ban list and bans from servers with it enabled', guild_ids=[botadminguild],
             options=[
               create_option(
                 name="userid",
                 description="ID of the user",
                 option_type=3,
                 required=True
               ),
               create_option(
                 name="reason",
                 description="The reason for the community ban",
                 option_type=3,
                 required=True
               )
             ])
@slash.permission(guild_id=botadminguild, permissions=[create_permission(botadminrole, SlashCommandPermissionType.ROLE, True)])
async def _communityban(ctx, userid, reason):
    if ctx.author.id not in botadmins:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    if ctx.channel != verificationchannel:
        await ctx.send("Please do the command in the verification channel", hidden=True)
        return
    print(reason)
    if reason == "" or reason == " ":
        await ctx.send("Please input a reason", hidden=True)
        return
    try:
        user = await bot.fetch_user(int(userid))
    except discord.NotFound:
        await ctx.send("User ID could not be found", hidden=True)
        return
    await ctx.defer()
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
        await guild.ban(user=user, reason=str(reason), delete_message_days=0)
        await modchan.send("Community Ban: " + str(user) + " - " + str(user.id) + " for " + reason)
    await ctx.send("Community ban successful")


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
    banid = shortuuid       .ShortUUID().random(length=22)
    embed = discord.Embed(title='Report', colour=0xe74c3c)
    embed.add_field(name='Banned User', value=str(user) + " - " + str(user.id), inline=True)
    embed.add_field(name='Server', value=guild.name + " - " + str(guild.id), inline=True)
    embed.add_field(name='Reason', value="None", inline=False)
    embed.add_field(name='Evidence', value="None", inline=False)
    embed.add_field(name='Ban Type', value="None", inline=False)
    embed.add_field(name='Ban Notes', value="None", inline=False)
    embed.add_field(name='Ban ID', value=str(banid))
    embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/708059652633526374.png', text=("Report " + str(
        datetime.datetime.now())[:-7]))
    await modchannel.send(content="I see you just banned " + str(user) + """
To help us categorize this ban, please do the following:
Press 🔨 to set the ban reason.
Press 📷 to add images or links to the evidence.
Press 📸 to erase evidence.
Press #️⃣ to select the ban type.
Press 🗒️ to add ban notes.
Press ✅ to submit the ban to the database.
You can press ❌ to cancel.""", embed=embed, components=[[
        Button(label='', id='🔨', emoji='🔨'),
        Button(label='', id='📷', emoji='📷'),
        Button(label='', id='📸', emoji='📸'),
        Button(label='', id='#️⃣', emoji='#️⃣'),
        Button(label='', id='🗒️', emoji='🗒️')], [
        Button(label='', id='✅', emoji='✅'),
        Button(label='', id='❌', emoji='❌')
    ]])


@slash.slash(name='autobanlist', description='retrieves the list of users on the auto ban list', guild_ids=guild_ids)
async def _autobanlist(ctx):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    await ctx.defer()
    guildinfo = conn.cursor()
    guildinfo.execute("SELECT * FROM reportList WHERE autoBan=1")
    rows = guildinfo.fetchall()
    embed = discord.Embed(title='Auto ban list', colour=0x000000)
    banlist = ""
    for row in rows:
        try:
            user = await bot.fetch_user(row[1])
        except discord.NotFound:
            user = "User not found"
        banlist += (str(user) + " - " + str(row[1]) + "\n" + "Reason: " + str(row[13]) + "\n" + "\n")
    embed.add_field(name="Users", value=banlist)
    embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/708059652633526374.png',
                     text=(str(datetime.datetime.now())[:-7]))
    guildinfo.close()
    await ctx.send(embed=embed)


bot.remove_command('help')


@slash.slash(name="help", description="Shows the list of commands", guild_ids=guild_ids)
async def _help(ctx):
    await ctx.send("""List of commands:
`/setmodchannel` - sets the bot's output to the current channel
`/report` - creates an editable report ticket for the user
`/info` - returns info about the reports the user has
`/data` - provides a link to the full database of individuals on the ban list
`/autobanlist` - retrieves the list of users on the auto ban list
`/autoban` - toggle to enable the bot to auto ban users on the auto ban list (only used in extreme circumstances)""")


@slash.slash(name='data', description='Gives a link to the ban database', guild_ids=guild_ids)
async def _data(ctx):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    await ctx.defer()
    with open('curdata.txt', 'r', encoding='utf-8') as w:
        datatosend = w.read()
    await ctx.send(datatosend)


@slash.slash(name='setmodchannel', description='Sets the mod channel for logs and bans to the current channel',
             guild_ids=guild_ids)
async def _setmodchannel(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    await ctx.defer()
    print(f'Connected to {ctx.guild.name}')
    guildinfo = conn.cursor()
    sqlcommand = """DELETE FROM guildsInfo WHERE guildID=?"""
    try:
        guildinfo.execute(sqlcommand, (ctx.guild.id,))
        conn.commit()
    except:
        print("expected fail")
    sqlcommand = """INSERT INTO guildsInfo (guildName,guildID,modChannelID,autoBan,updates) Values(?,?,?,?,?)"""
    guildinfo.execute(sqlcommand, (ctx.guild.name, ctx.guild.id, ctx.channel.id, int(0), int(1)))
    conn.commit()
    guildinfo.execute("SELECT * FROM guildsInfo")
    rows = guildinfo.fetchall()
    modchannels.clear()
    runningmodchannels.clear()
    for row in rows:
        modchannels.append(bot.get_channel(row[2]))
        runningmodchannels.append(0)
    await ctx.send("Set channel to " + str(ctx.channel))
    guildinfo.close()


@slash.slash(name='toggleupdates', description='Toggles whether the server receives info about updates to the database', guild_ids=guild_ids)
async def _toggleupdates(ctx):

    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    modchannel = await fetch_modchan(ctx.guild)
    if modchannel is None:
        await ctx.send("You need to set the mod channel with %setmodchannel to use that", hidden=True)
        return
    await ctx.defer()
    guildinfo = conn.cursor()
    guildinfo.execute("SELECT * FROM guildsInfo WHERE guildID=?", (int(ctx.guild.id),))
    row = guildinfo.fetchone()
    if row[4] == 1:
        guildinfo.execute("UPDATE guildsInfo SET updates=0 WHERE guildID=?", (int(ctx.guild.id),))
        await ctx.send("Database updates turned off")
    else:
        guildinfo.execute("UPDATE guildsInfo SET updates=1 WHERE guildID=?", (int(ctx.guild.id),))
        await ctx.send("Database updates turned on")


@slash.slash(name='autoban', description='toggle the autoban system for users with extreme offences', guild_ids=guild_ids)
async def _autoban(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    modchannel = await fetch_modchan(ctx.guild)
    if modchannel is None:
        await ctx.send("You need to set the mod channel with %setmodchannel to use that", hidden=True)
        return
    await ctx.defer()
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
                    await ctx.send(
                        "Warning: " + str(member) + " will be banned if you enable the auto ban list")
            await ctx.send("Enabling this will allow the bot to auto ban individuals with heinous "
                                   "offences\nDo you want to continue?")
            msg = await bot.wait_for("message", check=check, timeout=120)
            if msg.content.lower() == "y" or msg.content.lower() == "yes":
                for row2 in rows2:
                    try:
                        banuser = await bot.fetch_user(row2[1])
                    except discord.NotFound:
                        continue
                    await ctx.guild.ban(user=banuser, reason=str(row2[13]), delete_message_days=0)
                guildinfo.execute("UPDATE guildsInfo SET autoBan=1 WHERE guildID=?", (int(ctx.guild.id),))
                await ctx.send("Autoban list turned on")
                conn.commit()
                guildinfo.close()
                return
            else:
                await ctx.send("Autoban list turned off")
                guildinfo.close()
                return
        elif row[3] == 1:
            guildinfo.execute("UPDATE guildsInfo SET autoBan=0 WHERE guildID=?", (int(ctx.guild.id),))
            await ctx.send("Autoban list turned off")
            conn.commit()
            guildinfo.close()
            return


@slash.slash(name='report', description='creates an editable report ticket for the user', guild_ids=guild_ids, options=[
               create_option(
                 name="user",
                 description="User to report",
                 option_type=6,
                 required=False
               ),
               create_option(
                 name="userid",
                 description="ID of User to report",
                 option_type=3,
                 required=False
               )
             ])
async def _report(ctx, user=None, userid=None):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    modchannel = await fetch_modchan(ctx.guild)
    if modchannel is None:
        await ctx.send("You need to set the mod channel with %setmodchannel to use that", hidden=True)
        return
    if user is None:
        await ctx.send("Invalid User", hidden=True)
        return

    if not isinstance(user, str):
        user = user.id
    userid = int(user)
    try:
        user = await bot.fetch_user(userid)
    except discord.NotFound:
        await ctx.send("Invalid User ID", hidden=True)
        return
    await ctx.defer()
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
    senmsg="I see you just reported " + str(user) + """
To help us categorize this ban, please do the following:
Press 🔨 to set the ban reason.
Press 📷 to add images or links to the evidence.
Press 📸 to erase evidence.
Press #️⃣ to select the ban type.
Press 🗒️ to add ban notes.
Press ✅ to submit the ban to the database.
You can press ❌ to cancel."""
    reacto = await ctx.send(content=senmsg, embed=embed)
    await reacto.edit(content=senmsg, embed=embed, components=[[
        Button(label='', id='🔨', emoji='🔨'),
        Button(label='', id='📷', emoji='📷'),
        Button(label='', id='📸', emoji='📸'),
        Button(label='', id='#️⃣', emoji='#️⃣'),
        Button(label='', id='🗒️', emoji='🗒️')], [
        Button(label='', id='✅', emoji='✅'),
        Button(label='', id='❌', emoji='❌')
    ]])


@slash.slash(name='info', description='returns ban/report info on the user', guild_ids=guild_ids, options=[
               create_option(
                 name="user",
                 description="User to get info on",
                 option_type=6,
                 required=False
               ),
               create_option(
                 name="userid",
                 description="ID of User to get info on",
                 option_type=3,
                 required=False
               )
             ])
async def _info(ctx, user=None, userid=None):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send(hidden=True, content="You do not have the permissions to use that command")
        return
    if user is None:
        await ctx.send(hidden=True, content="Enter a user to use the command")
        return
    await ctx.defer()
    print("recieved")
    try:
        if not isinstance(user, str):
            user = user.id

        userid = int(user)
        print("success")
        # dumb code, fix later
        try:
            try:
                member = ctx.guild.get_member(int(userid))
                embed = discord.Embed(title='Member Info', color=0xfffffe)
                embed = await membersearch(embed, member)
            except:
                user = await bot.fetch_user(int(userid))
                embed = discord.Embed(title='User Info', color=0xfffffe)
                embed = await usersearch(embed, user)
        except Exception as e:
            print(e)
            await ctx.send("Invalid User ID")
            return
        reacto = await ctx.send(embed=embed)
        await reacto.edit(embed=embed, components=[[
            Button(label='', id='✅', emoji='✅'),
            Button(label='', id='❌', emoji='❌'),
            Button(label='', id='☠', emoji='☠')
        ]])
    except Exception as e:
        print(e)
        print("fail??")
        await ctx.send("Invalid User ID")

@bot.event
async def on_button_click(interaction):
    channel = bot.get_channel(interaction.channel.id)
    guild = interaction.guild
    user = guild.get_member(interaction.user.id)
    if user == bot.user:
        return
    try:
        message = await channel.fetch_message(interaction.message.id)
    except:
        print("unknown error")
        return

    def check(m):
        return m.author.id == user.id and m.channel == channel

    def check2(m):
        try:
            int(m.content)
        except ValueError:
            return False
        return 0 < int(m.content) < 20
    if message.author == bot.user:
        try:
            newEmbed = message.embeds[0]
            embed_dict = newEmbed.to_dict()
        except:
            await interaction.respond(type=6)
            return
        if embed_dict['color'] == 0x00FF00 or embed_dict['color'] == 0x000000:
            await interaction.respond(type=6)
            return
        if channel == verificationchannel:
            guildinfo = conn.cursor()
            if interaction.component.id == '✅':
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
                    return
                conn.commit()
                await banlistupdate(await bot.fetch_user(int(reported[-1])))
            elif interaction.component.id == '❌':
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
            await interaction.respond(type=6)
        else:
            if not user.guild_permissions.ban_members:
                await interaction.respond(content=(user.name + " you do not have permission to perform that action"))
                return
            await interaction.respond(type=6)
            if newEmbed.fields[0].name == "Banned User":
                if embed_dict['color'] == 0xe74c3b:
                    runningmodchannels[modchannels.index(channel)] = 0
                    embed_dict['color'] = 0xe74c3c
                elif embed_dict['color'] == 0xf1c40e:
                    embed_dict['color'] = 0xf1c40f
                    runningmodchannels[modchannels.index(channel)] = 0
                if interaction.component.id == '✅':
                    if embed_dict['color'] == 0xf1c40f:
                        embed_dict['color'] = 0x00FF00
                        newEmbed = discord.Embed.from_dict(embed_dict)
                        reported = newEmbed.fields[0].value.split()
                        reason = newEmbed.fields[2].value
                        evidence = newEmbed.fields[3].value
                        bantype = newEmbed.fields[4].value
                        bannotes = newEmbed.fields[5].value
                        banid = newEmbed.fields[6].value
                        if reason == "Loli content" or reason == "Real child pornography content":
                            evidence = "[Evidence removed due to sensitive content]"
                        guildinfo = conn.cursor()
                        sql = """INSERT INTO reportList (reportedUserName,reportedUserID,guildName,guildID,reason,
                        evidence,banType,banNotes,time, certified, banID, userNotes, autoBan, autoBanReason) 
                        Values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
                        try:
                            guildinfo.execute(sql, (
                                "PII removed", int(reported[-1]), "PII removed", int(guild.id), reason,
                                evidence,
                                bantype,
                                bannotes, str(datetime.datetime.now())[:-7], int(0), banid, "None", int(0), "None"))
                        except Exception as e:
                            print(e)
                            print("major error, kill")
                        conn.commit()
                        guildinfo.close()
                        await verifyban(newEmbed, await bot.fetch_user(int(reported[-1])))
                        await message.edit(content="_ _", embed=newEmbed)
                    else:
                        await channel.send("Please enter the ban type and ban reason before submitting")
                elif interaction.component.id == '🔨':
                    mesg = await channel.send('Enter a new ban reason')
                    try:
                        msg = await bot.wait_for("message", check=check, timeout=120)
                    except TimeoutError:
                        await mesg.delete()
                        return
                    try:
                        await mesg.delete()
                    except:
                        print("oof")
                    if newEmbed.fields[4].value != "None":
                        embed_dict['color'] = 0xf1c40f
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    newEmbed.set_field_at(2, name='Reason', value=msg.content, inline=False)
                    await msg.delete()
                    await message.edit(embed=newEmbed)
                elif interaction.component.id == '📷':
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
                        try:
                            msg = await bot.wait_for("message", check=check, timeout=1)
                            tosend = ""
                            for attachment in msg.attachments:
                                await attachment.save(attachment.filename)
                                msg2 = await imagechannel.send(file=discord.File(attachment.filename))
                                os.remove(attachment.filename)
                                if len(msg.attachments) > 1:
                                    tosend += msg2.attachments[0].url + "\n"
                                else:
                                    tosend = msg2.attachments[0].url
                                print(tosend)
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
                            await msg.delete()
                        except:
                            if runningmodchannels[modchannels.index(channel)] == 0:
                                break
                    await mesg.delete()
                elif interaction.component.id == '📸':
                    embed_dict['color'] = 0xe74c3c
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    newEmbed.set_field_at(3, name='Evidence', value="None", inline=False)
                    await message.edit(embed=newEmbed)
                elif interaction.component.id == '#️⃣':
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
19 - Other""")
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
                    await msg.delete()
                elif interaction.component.id == '🗒️':
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
                    await msg.delete()
                elif interaction.component.id == '❌':
                    newEmbed = discord.Embed(title="Report cancelled", color=0x000000)
                    await message.edit(content="_ _", embed=newEmbed)
            elif newEmbed.fields[0].name == "Member" or newEmbed.fields[0].name == "User":
                if interaction.component.id == '✅':
                    embed_dict['color'] = 0x00FF00
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    await message.edit(embed=newEmbed)
                elif interaction.component.id == '❌':
                    embed_dict['color'] = 0x000000
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    user2 = await bot.fetch_user(int(newEmbed.fields[0].value.split()[-1]))
                    try:
                        await guild.kick(user=user2, reason="Failed verification")
                    except (PermissionError, discord.errors.Forbidden):
                        await channel.send("I don't have permissions to kick that user")
                        return
                    await message.edit(embed=newEmbed)
                    await channel.send(str(user2) + " was kicked from the server.")
                elif interaction.component.id == '☠':
                    embed_dict['color'] = 0x000000
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    user2 = await bot.fetch_user(int(newEmbed.fields[0].value.split()[-1]))
                    try:
                        await guild.ban(user=user2, reason="Failed verification", delete_message_days=0)
                    except (PermissionError, discord.errors.Forbidden):
                        await channel.send("I don't have permissions to ban that user")
                        return
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
        await member.guild.ban(user=member, reason="Auto community ban", delete_message_days=0)
        await modchannel.send("Community Ban: " + str(member) + " - " + str(member.id) + " for " + reason)
        guildinfo.close()
    embed = discord.Embed(title='New member joined', color=0xfffffe)
    embed = await membersearch(embed, member)
    await modchannel.send(embed=embed, components=[[
            Button(label='', id='✅', emoji='✅'),
            Button(label='', id='❌', emoji='❌'),
            Button(label='', id='☠', emoji='☠')
        ]])


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.send(hidden=True, content="You do not have the permissions to use that command.")
    elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
        return
    elif isinstance(error, discord.Forbidden):
        await ctx.send("That action is forbidden", hidden=True)
    else:
        raise error

@bot.event
async def on_slash_command_error(ctx, ex):
    if isinstance(ex, MissingPermissions):
        await ctx.send("You do not have the permissions to use that command.", hidden=True)
    elif isinstance(ex, discord.ext.commands.errors.CommandNotFound):
        return
    elif isinstance(ex, discord.Forbidden):
        await ctx.send("That action is forbidden", hidden=True)
    else:
        raise ex


bot.run(TOKEN)
