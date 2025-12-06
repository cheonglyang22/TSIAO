import os
import socket
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# 여기에 본인 마인크래프트 서버 IP 입력
SERVER_IP = "121.55.191.103"
SERVER_PORT = 25565

# 봇 설정
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 포트가 열렸는지 확인하는 함수
def check_port(ip, port, timeout=1):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except:
        return False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {synced}")
    except Exception as e:
        print(e)

# /서버상태 명령
@bot.tree.command(name="서버상태", description="마인크래프트 서버 열렸는지 확인합니다.")
async def server_status(interaction: discord.Interaction):

    is_open = check_port(SERVER_IP, SERVER_PORT)

    if is_open:
        await interaction.response.send_message("🟢 **서버 열려 있음! 접속 가능해요!**")
    else:
        await interaction.response.send_message("🔴 **서버 닫혀 있음.** 현재 접속 불가")

bot.run(TOKEN)
