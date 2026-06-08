import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import datetime
from dotenv import load_dotenv

if os.path.exists('.env'):
    load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.data_file = "schedule.json"
        self.config_file = "embed_config.json"
        self.schedules = self.load_schedules()
        self.embed_config = self.load_embed_config()

    async def setup_hook(self):
        self.tree.add_command(gacha_group)
        await self.tree.sync()
        self.daily_dm_alert.start()

    def load_schedules(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {"games": [], "events": []}
        return {"games": [], "events": []}

    def save_schedules(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.schedules, f, ensure_ascii=False, indent=4)

    def load_embed_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        # 3종류의 레이아웃 기본값 세팅
        return {
            # 1. 개인 DM 알림 메시지 설정
            "title": "⏰ [가챠 일정 알림]",
            "description": "안녕하세요 {user}님!\n\n게임: `{game_name}`\n이벤트: `{event_name}`\n남은 기간: **{left}**\n\n💡 완료하셨다면 아래의 ❌ 이모지를 클릭 시 스케쥴이 삭제됩니다.",
            "hexcolor": "5865F2",
            "author_text": "{server_name} 알리미",
            "author_image": "{server_icon}",
            "footer_text": "푸른 안개 | 서브컬쳐",
            "footer_image": "",
            "timestamp": "yes",
            "main_image": "",
            "thumbnail": "",

            # 2. 일정 목록창 설정
            "list_title": "📅 {game_name} 진행 중인 이벤트 목록",
            "list_description": "현재 등록된 {game_name}의 일정 리스트입니다.\n\n{event_list}",
            "list_hexcolor": "2F3136",

            # 3. 게임 목록창 설정
            "game_list_title": "🎮 서버 등록 게임 목록",
            "game_list_description": "현재 가챠 알림이 지원되는 게임들입니다.\n\n{game_list}",
            "game_list_hexcolor": "7289DA"
        }

    def save_embed_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.embed_config, f, ensure_ascii=False, indent=4)

    def parse_placeholders(self, text, member: discord.Member, guild: discord.Guild, game_name="", event_name="",
                           left_time=""):
        if not text:
            return ""

        user_nick = member.global_name if member.global_name else member.name
        user_display = member.display_name
        server_name = guild.name if guild else "서버 알림"
        server_icon = str(guild.icon.url) if guild and guild.icon else ""

        mapping = {
            "{user_nick}": user_nick,
            "{user}": user_display,
            "{left}": left_time,
            "{server_name}": server_name,
            "{server_icon}": server_icon,
            "{game_name}": game_name,
            "{event_name}": event_name
        }

        parsed_text = text
        for placeholder, real_value in mapping.items():
            parsed_text = parsed_text.replace(placeholder, str(real_value))
        return parsed_text

    def build_custom_embed(self, member: discord.Member, guild: discord.Guild, game_name, event_name, left_time,
                           embed_type="message", list_content_str=""):
        cfg = self.embed_config

        # [A] 일정 목록창 빌드
        if embed_type == "schedule_list":
            title_raw = cfg.get("list_title", "📅 {game_name} 진행 중인 이벤트 목록")
            desc_raw = cfg.get("list_description", "현재 등록된 {game_name}의 일정 리스트입니다.\n\n{event_list}")
            color_hex = cfg.get("list_hexcolor", "2F3136")

            desc_raw = desc_raw.replace("{event_list}", list_content_str)
            title_parsed = self.parse_placeholders(title_raw, member, guild, game_name=game_name)
            desc_parsed = self.parse_placeholders(desc_raw, member, guild, game_name=game_name)

            try:
                color_val = int(color_hex.replace("#", ""), 16)
            except ValueError:
                color_val = int("2F3136", 16)

            return discord.Embed(title=title_parsed, description=desc_parsed, color=color_val)

        # [B] 게임 목록창 빌드
        elif embed_type == "game_list":
            title_raw = cfg.get("game_list_title", "🎮 서버 등록 게임 목록")
            desc_raw = cfg.get("game_list_description", "현재 가챠 알림이 지원되는 게임들입니다.\n\n{game_list}")
            color_hex = cfg.get("game_list_hexcolor", "7289DA")

            desc_raw = desc_raw.replace("{game_list}", list_content_str)
            title_parsed = self.parse_placeholders(title_raw, member, guild)
            desc_parsed = self.parse_placeholders(desc_raw, member, guild)

            try:
                color_val = int(color_hex.replace("#", ""), 16)
            except ValueError:
                color_val = int("7289DA", 16)

            return discord.Embed(title=title_parsed, description=desc_parsed, color=color_val)

        # [C] 기본 개인 DM 메시지 임베드 빌드
        else:
            title_parsed = self.parse_placeholders(cfg["title"], member, guild, game_name, event_name, left_time)
            desc_parsed = self.parse_placeholders(cfg["description"], member, guild, game_name, event_name, left_time)

            try:
                color_val = int(cfg["hexcolor"].replace("#", ""), 16)
            except ValueError:
                color_val = int("5865F2", 16)

            embed = discord.Embed(title=title_parsed, description=desc_parsed, color=color_val)

            if cfg["author_text"]:
                embed.set_author(
                    name=self.parse_placeholders(cfg["author_text"], member, guild, game_name, event_name, left_time),
                    icon_url=self.parse_placeholders(cfg["author_image"], member, guild, game_name, event_name,
                                                     left_time) or None
                )
            if cfg["footer_text"]:
                embed.set_footer(
                    text=self.parse_placeholders(cfg["footer_text"], member, guild, game_name, event_name, left_time),
                    icon_url=self.parse_placeholders(cfg["footer_image"], member, guild, game_name, event_name,
                                                     left_time) or None
                )
            if cfg["timestamp"].lower() == "yes":
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

            if cfg["main_image"]:
                main_url = self.parse_placeholders(cfg["main_image"], member, guild, game_name, event_name, left_time)
                if main_url.startswith("http"): embed.set_image(url=main_url)
            if cfg["thumbnail"]:
                thumb_url = self.parse_placeholders(cfg["thumbnail"], member, guild, game_name, event_name, left_time)
                if thumb_url.startswith("http"): embed.set_thumbnail(url=thumb_url)

            return embed

    @tasks.loop(hours=24.0)
    async def daily_dm_alert(self):
        await self.wait_until_ready()
        now = datetime.datetime.now()

        active_events = []
        for event in self.schedules.get("events", []):
            end_time = datetime.datetime.fromisoformat(event["end_time"])
            if end_time > now:
                active_events.append(event)
        self.schedules["events"] = active_events
        self.save_schedules()

        for event in self.schedules.get("events", []):
            end_time = datetime.datetime.fromisoformat(event["end_time"])
            time_left = end_time - now

            if 0 < time_left.days < 7:
                days = time_left.days
                hours = time_left.seconds // 3600
                left_str = f"{days}일 {hours}시간"

                for guild in self.guilds:
                    async for member in guild.fetch_members(limit=None):
                        if member.bot: continue
                        try:
                            embed = self.build_custom_embed(member, guild, event['game_name'], event['event_name'],
                                                            left_str, "message")
                            msg = await member.send(embed=embed)
                            await msg.add_reaction("❌")
                        except discord.Forbidden:
                            continue


bot = MyBot()


@bot.event
async def on_ready():
    print(f"🤖 로그인 완료: {bot.user.name}")


# ================= [ 모달 UI 컴포넌트 구역 ] =================

class BasicInfoModal(discord.ui.Modal, title="기본 정보 수정"):
    title_input = discord.ui.TextInput(label="Embed Title (제목)", required=False)
    desc_input = discord.ui.TextInput(label="Description (본문)", style=discord.TextStyle.paragraph, required=False)
    color_input = discord.ui.TextInput(label="Hex Color (예: 5865F2)", max_length=7, required=False)

    def __init__(self, bot_obj):
        super().__init__()
        self.bot = bot_obj
        self.title_input.default = self.bot.embed_config["title"]
        self.desc_input.default = self.bot.embed_config["description"]
        self.color_input.default = self.bot.embed_config["hexcolor"]

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.embed_config["title"] = self.title_input.value or ""
        self.bot.embed_config["description"] = self.desc_input.value or ""
        self.bot.embed_config["hexcolor"] = self.color_input.value or "5865F2"
        self.bot.save_embed_config()
        await interaction.response.send_message("✅ 알림 기본 정보가 저장되었습니다.", ephemeral=True)


class AuthorModal(discord.ui.Modal, title="작성자(Author) 정보 수정"):
    text_input = discord.ui.TextInput(label="Author Text (이름)", required=False)
    img_input = discord.ui.TextInput(label="Author Image (링크 혹은 {server_icon})", required=False)

    def __init__(self, bot_obj):
        super().__init__()
        self.bot = bot_obj
        self.text_input.default = self.bot.embed_config["author_text"]
        self.img_input.default = self.bot.embed_config["author_image"]

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.embed_config["author_text"] = self.text_input.value or ""
        self.bot.embed_config["author_image"] = self.img_input.value or ""
        self.bot.save_embed_config()
        await interaction.response.send_message("✅ 알림 작성자 정보가 저장되었습니다.", ephemeral=True)


class FooterModal(discord.ui.Modal, title="하단(Footer) 정보 수정"):
    text_input = discord.ui.TextInput(label="Footer Text (내용)", required=False)
    img_input = discord.ui.TextInput(label="Footer Image Link", required=False)

    def __init__(self, bot_obj):
        super().__init__()
        self.bot = bot_obj
        self.text_input.default = self.bot.embed_config["footer_text"]
        self.img_input.default = self.bot.embed_config["footer_image"]

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.embed_config["footer_text"] = self.text_input.value or ""
        self.bot.embed_config["footer_image"] = self.img_input.value or ""
        self.bot.save_embed_config()
        await interaction.response.send_message("✅ 알림 하단 정보가 저장되었습니다.", ephemeral=True)


class ImagesModal(discord.ui.Modal, title="이미지 및 타임스탬프 수정"):
    main_input = discord.ui.TextInput(label="Main Image Link", required=False)
    thumb_input = discord.ui.TextInput(label="Thumbnail Link", required=False)
    ts_input = discord.ui.TextInput(label="Timestamp 활성화 (yes / no)", max_length=3, required=False)

    def __init__(self, bot_obj):
        super().__init__()
        self.bot = bot_obj
        self.main_input.default = self.bot.embed_config["main_image"]
        self.thumb_input.default = self.bot.embed_config["thumbnail"]
        self.ts_input.default = self.bot.embed_config["timestamp"]

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.embed_config["main_image"] = self.main_input.value or ""
        self.bot.embed_config["thumbnail"] = self.thumb_input.value or ""
        self.bot.embed_config["timestamp"] = "yes" if self.ts_input.value.lower() in ["yes", "y", "예"] else "no"
        self.bot.save_embed_config()
        await interaction.response.send_message("✅ 알림 이미지 및 타임스탬프 설정이 변경되었습니다.", ephemeral=True)


class ScheduleListModal(discord.ui.Modal, title="일정목록창 임베드 디자인 설정"):
    title_input = discord.ui.TextInput(label="일정목록창 타이틀 제목", required=False)
    desc_input = discord.ui.TextInput(label="일정목록창 본문 ({event_list} 포함 필수)", style=discord.TextStyle.paragraph,
                                      required=False)
    color_input = discord.ui.TextInput(label="Hex Color 색상코드", max_length=7, required=False)

    def __init__(self, bot_obj):
        super().__init__()
        self.bot = bot_obj
        self.title_input.default = self.bot.embed_config.get("list_title", "")
        self.desc_input.default = self.bot.embed_config.get("list_description", "")
        self.color_input.default = self.bot.embed_config.get("list_hexcolor", "")

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.embed_config["list_title"] = self.title_input.value or "📅 {game_name} 진행 중인 이벤트 목록"
        self.bot.embed_config["list_description"] = self.desc_input.value or "{event_list}"
        self.bot.embed_config["list_hexcolor"] = self.color_input.value or "2F3136"
        self.bot.save_embed_config()
        await interaction.response.send_message("✅ 일정목록창 커스텀 디자인이 저장되었습니다.", ephemeral=True)


class GameListModal(discord.ui.Modal, title="게임목록창 임베드 디자인 설정"):
    title_input = discord.ui.TextInput(label="게임목록창 타이틀 제목", required=False)
    desc_input = discord.ui.TextInput(label="게임목록창 본문 ({game_list} 포함 필수)", style=discord.TextStyle.paragraph,
                                      required=False)
    color_input = discord.ui.TextInput(label="Hex Color 색상코드", max_length=7, required=False)

    def __init__(self, bot_obj):
        super().__init__()
        self.bot = bot_obj
        self.title_input.default = self.bot.embed_config.get("game_list_title", "")
        self.desc_input.default = self.bot.embed_config.get("game_list_description", "")
        self.color_input.default = self.bot.embed_config.get("game_list_hexcolor", "")

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.embed_config["game_list_title"] = self.title_input.value or "🎮 서버 등록 게임 목록"
        self.bot.embed_config["game_list_description"] = self.desc_input.value or "{game_list}"
        self.bot.embed_config["game_list_hexcolor"] = self.color_input.value or "7289DA"
        self.bot.save_embed_config()
        await interaction.response.send_message("✅ 게임목록창 커스텀 디자인이 저장되었습니다.", ephemeral=True)


class EmbedConfigView(discord.ui.View):
    def __init__(self, bot_obj):
        super().__init__(timeout=None)
        self.bot = bot_obj

    @discord.ui.button(label="edit basic information", style=discord.ButtonStyle.secondary)
    async def edit_basic(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BasicInfoModal(self.bot))

    @discord.ui.button(label="edit author", style=discord.ButtonStyle.secondary)
    async def edit_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AuthorModal(self.bot))

    @discord.ui.button(label="edit footer", style=discord.ButtonStyle.secondary)
    async def edit_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FooterModal(self.bot))

    @discord.ui.button(label="edit images / timestamp", style=discord.ButtonStyle.secondary)
    async def edit_images(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImagesModal(self.bot))


# ================= [ 서브 커맨드 트리 그룹 관리 ] =================

gacha_group = app_commands.Group(name="가챠", description="가챠 알림 및 스케줄 시스템 명령어")
setting_group = app_commands.Group(name="설정", description="가챠 알림 양식 및 설정 제어 명령어")
schedule_group = app_commands.Group(name="일정", description="가챠 일정 추가 및 조회/삭제 명령어")
game_group = app_commands.Group(name="게임", description="서버 등록 게임 관리 명령어")

gacha_group.add_command(setting_group)
gacha_group.add_command(schedule_group)
gacha_group.add_command(game_group)


# --- [도움말] /가챠 도움말 ---
@gacha_group.command(name="도움말", description="사용 가능한 가챠 알림 시스템 명령어를 확인합니다.")
async def help_command(interaction: discord.Interaction):
    is_admin = interaction.permissions.administrator
    embed = discord.Embed(
        title="📖 가챠 알림 스케줄러 도움말",
        description=f"안녕하세요, **{interaction.user.display_name}**님!\n현재 권한 상태: {'👑 **서버 관리자**' if is_admin else '👤 **일반 유저**'}",
        color=int("5865F2", 16)
    )
    embed.add_field(
        name="👤 일반 유저 명령어",
        value="`/가챠 일정 추가 [게임이름] [이벤트이름] [일:시]`\n"
              "`/가챠 일정 목록 [게임이름]`\n"
              "`/가챠 일정 삭제 [게임이름] [이벤트이름]`\n"
              "`/가챠 게임 목록`\n"
              "`/가챠 도움말`",
        inline=False
    )
    if is_admin:
        embed.add_field(
            name="👑 관리자 전용 명령어",
            value="`/가챠 설정 게임추가 [게임이름]`\n"
                  "`/가챠 설정 메세지` - DM 알림창 전용 편집\n"
                  "`/가챠 설정 일정목록창` - 일정 리스트창 전용 편집\n"
                  "`/가챠 설정 게임목록창` - 허가 게임 목록창 전용 편집\n"
                  "`/가챠 테스트메세지 [게임이름] [이벤트이름]`",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- ✨ [1/3] /가챠 설정 메세지 (관리자 전용) ---
@setting_group.command(name="메세지", description="[관리자] 개인 DM 알림(알림 발송용)에 사용될 임베드를 커스텀 편집합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def config_message(interaction: discord.Interaction):
    view = EmbedConfigView(bot)
    preview_embed = bot.build_custom_embed(interaction.user, interaction.guild, "테스트_게임", "테스트_이벤트", "3일 5시간",
                                           "message")
    await interaction.response.send_message(
        "⚙️ **가챠 알림(DM) 임베드 커스텀 구성**\n하단의 각 서브 카테고리 버튼을 누르면 입력창이 열립니다.\n\n**[알림 메시지 미리보기 양식]**",
        embed=preview_embed,
        view=view,
        ephemeral=True
    )


# --- ✨ [2/3] /가챠 설정 일정목록창 (관리자 전용) ---
@setting_group.command(name="일정목록창", description="[관리자] '/가챠 일정 목록' 조회 시 사용될 임베드를 커스텀 편집합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def config_schedule_list_window(interaction: discord.Interaction):
    await interaction.response.send_modal(ScheduleListModal(bot))


# --- ✨ [3/3] /가챠 설정 게임목록창 (관리자 전용) ---
@setting_group.command(name="게임목록창", description="[관리자] '/가챠 게임 목록' 조회 시 사용될 임베드를 커스텀 편집합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def config_game_list_window(interaction: discord.Interaction):
    await interaction.response.send_modal(GameListModal(bot))


# --- [관리자] /가챠 설정 게임추가 ---
@setting_group.command(name="게임추가", description="[관리자] 허가할 가챠 대상 게임 목록을 등록합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def add_game(interaction: discord.Interaction, 게임이름: str):
    if 게임이름 in bot.schedules["games"]:
        await interaction.response.send_message(f"❌ `{게임이름}`은(는) 이미 등록된 게임입니다.", ephemeral=True)
        return
    bot.schedules["games"].append(게임이름)
    bot.save_schedules()
    await interaction.response.send_message(f"✅ 게임 `{게임이름}` 등록이 성공적으로 완료되었습니다.")


# --- /가챠 게임 목록 (디자인 분리 전동 반영) ---
@game_group.command(name="목록", description="서버에 추가되어 알림 등록이 허가된 게임 목록들을 모두 확인합니다.")
async def list_games(interaction: discord.Interaction):
    registered_games = bot.schedules.get("games", [])
    if not registered_games:
        game_list_str = "현재 서버에 등록된 게임이 하나도 없습니다. 관리자에게 추가를 요청하세요."
    else:
        game_list_str = "\n".join([f"**{idx}. {game}**" for idx, game in enumerate(registered_games, 1)])

    list_embed = bot.build_custom_embed(
        member=interaction.user,
        guild=interaction.guild,
        game_name="",
        event_name="",
        left_time="",
        embed_type="game_list",
        list_content_str=game_list_str
    )
    await interaction.response.send_message(embed=list_embed)


# --- /가챠 테스트메세지 (관리자 전용) ---
@gacha_group.command(name="테스트메세지", description="[관리자] 등록된 서식대로 본인에게 임베드 테스트 DM을 즉시 전송합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def test_message(interaction: discord.Interaction, 게임이름: str, 이벤트이름: str):
    try:
        processed_name = 이벤트이름.replace(" ", "_")
        embed = bot.build_custom_embed(interaction.user, interaction.guild, 게임이름, processed_name, "5일 23시간 (테스트)",
                                       "message")
        msg = await interaction.user.send(embed=embed)
        await msg.add_reaction("❌")
        await interaction.response.send_message("📬 본인의 개인 디엠(DM)으로 테스트 알림 임베드를 성공적으로 전송했습니다!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ 디엠을 보낼 수 없습니다. 개인 메시지 수락 상태를 체크해주세요.", ephemeral=True)


# --- /가챠 일정 추가 ---
@schedule_group.command(name="추가", description="특정 게임의 새로운 이벤트 가챠 일정을 등록합니다.")
async def add_event_schedule(interaction: discord.Interaction, 게임이름: str, 이벤트이름: str, 기간: str):
    if 게임이름 not in bot.schedules["games"]:
        await interaction.response.send_message(f"❌ 등록되지 않은 게임입니다. 관리자에게 먼저 게임 추가를 요청하세요.", ephemeral=True)
        return
    try:
        days, hours = map(int, 기간.split(":"))
    except ValueError:
        await interaction.response.send_message("❌ 기간 지정 양식이 잘못되었습니다. `일:시` 형식으로 써주세요. (예: 5:12)", ephemeral=True)
        return

    processed_name = 이벤트이름.replace(" ", "_")
    end_time = datetime.datetime.now() + datetime.timedelta(days=days, hours=hours)

    bot.schedules["events"].append({
        "game_name": 게임이름,
        "event_name": processed_name,
        "end_time": end_time.isoformat()
    })
    bot.save_schedules()
    await interaction.response.send_message(
        f"📅 **새 가챠 일정 접수**\n• 게임: `{게임이름}`\n• 이벤트: `{processed_name}`\n• 마감까지: {days}일 {hours}시간 남음")


# --- /가챠 일정 목록 (디자인 분리 전동 반영) ---
@schedule_group.command(name="목록", description="선택한 게임에 등록되어 현재 진행 중인 이벤트 목록과 남은 시간을 보여줍니다.")
async def list_events(interaction: discord.Interaction, 게임이름: str):
    if 게임이름 not in bot.schedules["games"]:
        await interaction.response.send_message("❌ 목록에 지정된 타겟 게임이 존재하지 않습니다.", ephemeral=True)
        return

    now = datetime.datetime.now()
    game_events = [e for e in bot.schedules.get("events", []) if e["game_name"] == 게임이름]

    valid_events = []
    lines = []

    for idx, ev in enumerate(game_events, 1):
        end_time = datetime.datetime.fromisoformat(ev["end_time"])
        if end_time > now:
            valid_events.append(ev)
            diff = end_time - now
            hours_left = diff.seconds // 3600
            lines.append(f"**{idx}. {ev['event_name']}**\n└ ⏳ 남은 시간: {diff.days}일 {hours_left}시간")

    if not lines:
        list_str = "현재 진행 중인 예정된 가챠 이벤트가 존재하지 않습니다."
    else:
        list_str = "\n".join(lines)

    list_embed = bot.build_custom_embed(
        member=interaction.user,
        guild=interaction.guild,
        game_name=게임이름,
        event_name="",
        left_time="",
        embed_type="schedule_list",
        list_content_str=list_str
    )
    await interaction.response.send_message(embed=list_embed)


# --- /가챠 일정 삭제 ---
@schedule_group.command(name="삭제", description="지정한 게임의 특정 가챠 이벤트를 데이터베이스에서 즉시 수동 삭제합니다.")
async def delete_event(interaction: discord.Interaction, 게임이름: str, 이벤트이름: str):
    processed_name = 이벤트이름.replace(" ", "_")
    origin_count = len(bot.schedules.get("events", []))

    bot.schedules["events"] = [
        e for e in bot.schedules["events"]
        if not (e["game_name"] == 게임이름 and e["event_name"] == processed_name)
    ]

    if len(bot.schedules["events"]) == origin_count:
        await interaction.response.send_message(f"❌ 일치하는 일정(`{게임이름}` - `{processed_name}`)을 찾을 수 없습니다.", ephemeral=True)
    else:
        bot.save_schedules()
        await interaction.response.send_message(f"🗑️ `{게임이름}`의 `{processed_name}` 일정을 리스트에서 강제 수동 삭제 처리했습니다.")


# --- 에러 처리 핸들러 코너 ---
@config_message.error
@config_schedule_list_window.error
@config_game_list_window.error
@add_game.error
@test_message.error
async def admin_perms_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ 이 기능은 서버 관리자 권한이 있는 분들만 컨트롤할 수 있습니다.", ephemeral=True)


# --- DM 이모지 반응 자동 제거 시스템 ---
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id or str(payload.emoji) != "❌":
        return

    if payload.guild_id is None:
        user = await bot.fetch_user(payload.user_id)
        channel = await bot.get_or_create_dm(user)
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if message.author.id == bot.user.id and len(message.embeds) > 0:
            target_embed = message.embeds[0]

            search_pool = ""
            if target_embed.title: search_pool += target_embed.title
            if target_embed.description: search_pool += target_embed.description
            if target_embed.author and target_embed.author.name: search_pool += target_embed.author.name
            if target_embed.footer and target_embed.footer.text: search_pool += target_embed.footer.text

            matched_event = None
            for event in bot.schedules.get("events", []):
                if event["game_name"] in search_pool and event["event_name"] in search_pool:
                    matched_event = event
                    break

            if matched_event:
                g_name = matched_event["game_name"]
                e_name = matched_event["event_name"]

                bot.schedules["events"] = [
                    e for e in bot.schedules["events"]
                    if not (e["game_name"] == g_name and e["event_name"] == e_name)
                ]
                bot.save_schedules()
                await channel.send(f"✅ `{g_name}`의 `{e_name}` 가챠 임무를 완수했습니다! 스케줄을 데이터에서 영구 삭제했습니다.")
            else:
                await channel.send("⚠️ 이미 마감되어 처리되었거나 스케줄 관리 테이블에서 찾을 수 없습니다.")


# 토큰 입력 후 구동
bot.run('MTUxMzU0NzI0MTIwNDM1MTA4Nw.GTVY_9.LAhgn9UvazMMCUBtu9GA-NQnmCiU7TxePaQT-s')
