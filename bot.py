import os
import socket
import time
import statistics
import asyncio
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

# 포트가 열렸는지 확인하는 함수 (간단 체크)
def check_port(ip, port, timeout=1):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except:
        return False

# 단일 TCP connect 측정 (동기함수; asyncio.to_thread로 호출해서 사용)
def measure_once(host, port, timeout=2.0):
    start = time.perf_counter()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        end = time.perf_counter()
        return True, (end - start) * 1000.0
    except Exception:
        end = time.perf_counter()
        return False, (end - start) * 1000.0

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {synced}")
    except Exception as e:
        print("Slash sync error:", e)

# /서버상태 명령 (기존)
@bot.tree.command(name="서버상태", description="마인크래프트 서버 열렸는지 확인합니다.")
async def server_status(interaction: discord.Interaction):
    is_open = check_port(SERVER_IP, SERVER_PORT)

    if is_open:
        await interaction.response.send_message("🟢 **서버 열려 있음! 접속 가능해요!**")
    else:
        await interaction.response.send_message("🔴 **서버 닫혀 있음.** 현재 접속 불가")

# /ping 명령 추가: tries 인자로 시도 횟수 지정 가능 (기본 5)
@bot.tree.command(name="ping", description="마인크래프트 서버의 실제 지연시간을 측정합니다.")
@app_commands.describe(tries="측정 시도 횟수 (기본 5)")
async def ping(interaction: discord.Interaction, tries: int = 5):
    # 즉시 응답 지연 표시 (슬래시 커맨드)
    await interaction.response.defer()

    if tries < 1:
        tries = 1
    if tries > 20:
        tries = 20  # 너무 큰 값 방지

    times = []
    fail_count = 0

    # 측정 루프 (블로킹 측정은 to_thread로 실행)
    for i in range(tries):
        ok, ms = await asyncio.to_thread(measure_once, SERVER_IP, SERVER_PORT, 2.0)
        if ok:
            times.append(ms)
        else:
            fail_count += 1
        # 약간의 간격을 둠
        await asyncio.sleep(0.12)

    # WebSocket latency (봇 ↔ 디스코드)
    ws_ping = round(bot.latency * 1000)

    if not times:
        # 모두 실패
        await interaction.followup.send(
            f"🔴 서버에 연결할 수 없습니다. 모든 시도({tries}) 실패했습니다.\n"
            f"서버: `{SERVER_IP}:{SERVER_PORT}`\n"
            f"요청자: {interaction.user.mention}\n"
            f"웹소켓 핑(봇↔디스코드): `{ws_ping} ms`"
        )
        return

    mn = min(times)
    av = statistics.mean(times)
    mx = max(times)

    embed = discord.Embed(
        title="서버 핑 결과",
        description=f"`{SERVER_IP}:{SERVER_PORT}`",
        color=0x2F3136
    )
    embed.add_field(name="요청자", value=interaction.user.mention, inline=True)
    embed.add_field(name="시도 횟수", value=f"{tries} (성공 {len(times)}, 실패 {fail_count})", inline=True)
    embed.add_field(name="웹소켓 핑", value=f"`{ws_ping} ms`", inline=True)
    embed.add_field(name="최소", value=f"`{mn:.1f} ms`", inline=True)
    embed.add_field(name="평균", value=f"`{av:.1f} ms`", inline=True)
    embed.add_field(name="최대", value=f"`{mx:.1f} ms`", inline=True)
    embed.set_footer(text="측정 방식: TCP connect (서버 접속 시도 기반, 방화벽/포트포워딩 영향 받음)")

    await interaction.followup.send(embed=embed)

bot.run(TOKEN)
