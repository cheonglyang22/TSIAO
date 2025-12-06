import os
import socket
import time
import statistics
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# 서버 표시용 라벨 (IP를 노출하지 않기 위해 레이블만 사용)
SERVER_LABEL = "마인크래프트 서버"
# 실제 검사할 IP/포트 (내부에서만 사용, 출력에는 절대 노출하지 않음)
SERVER_IP = "121.55.191.103"
SERVER_PORT = 25565

# 봇 설정
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 단일 TCP connect 측정 (동기 함수 - to_thread로 호출)
def measure_once(host: str, port: int, timeout: float = 2.0):
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

# 기존 서버상태 명령 (IP는 출력하지 않음)
@bot.tree.command(name="서버상태", description="마인크래프트 서버 열렸는지 확인합니다.")
async def server_status(interaction: discord.Interaction):
    await interaction.response.defer()
    ok, _ = await asyncio.to_thread(measure_once, SERVER_IP, SERVER_PORT, 1.0)
    if ok:
        await interaction.followup.send(f"🟢 **{SERVER_LABEL} 열려 있음! 접속 가능해요!**\n(민감 정보는 표시하지 않습니다.)")
    else:
        await interaction.followup.send(f"🔴 **{SERVER_LABEL} 닫혀 있음.** 현재 접속 불가\n(포트포워딩/방화벽/서버 상태를 확인하세요.)")

# /ping 명령: tries 인자(기본 5, 최대 20)
@bot.tree.command(name="ping", description="서버의 실제 지연시간을 측정합니다.)")
@app_commands.describe(tries="측정 시도 횟수 (1~20, 기본 5)")
async def ping(interaction: discord.Interaction, tries: int = 5):
    await interaction.response.defer()  # 슬래시 커맨드 대기 표시

    if tries < 1:
        tries = 1
    if tries > 20:
        tries = 20

    times = []
    fail_count = 0

    # 측정 루프 (blocking 측정은 to_thread로 수행)
    for i in range(tries):
        ok, ms = await asyncio.to_thread(measure_once, SERVER_IP, SERVER_PORT, 2.0)
        if ok:
            times.append(ms)
        else:
            fail_count += 1
        await asyncio.sleep(0.12)

    ws_ping = round(bot.latency * 1000)

    if not times:
        # 모든 시도 실패
        await interaction.followup.send(
            f"🔴 **{SERVER_LABEL}에 연결할 수 없습니다.** 모든 시도({tries}) 실패했습니다.\n"
            f"요청자: {interaction.user.mention}\n"
            f"웹소켓 핑 (봇 ↔ Discord): `{ws_ping} ms`\n\n"
            f"(참고: IP/민감 정보는 표시하지 않습니다)"
        )
        return

    mn = min(times)
    av = statistics.mean(times)
    mx = max(times)

    embed = discord.Embed(
        title=f"{SERVER_LABEL} 핑 결과",
        description="(PORT:25565의 왕복 지연시간 측정)",
        color=0x2F3136
    )
    embed.add_field(name="요청자", value=interaction.user.mention, inline=True)
    embed.add_field(name="시도 횟수", value=f"{tries} (성공 {len(times)}, 실패 {fail_count})", inline=True)
    embed.add_field(name="웹소켓 핑", value=f"`{ws_ping} ms`", inline=True)
    embed.add_field(name="최소", value=f"`{mn:.1f} ms`", inline=True)
    embed.add_field(name="평균", value=f"`{av:.1f} ms`", inline=True)
    embed.add_field(name="최대", value=f"`{mx:.1f} ms`", inline=True)
    embed.set_footer(text="측정 방식: TCP connect 기준. 포트포워딩/방화벽 영향 받을 수 있음.")

    await interaction.followup.send(embed=embed)

bot.run(TOKEN)
