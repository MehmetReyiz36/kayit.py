# bot.py
import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timezone
import asyncio
import json

# ----------------------------------------
# LOAD ENV
# ----------------------------------------
load_dotenv()
TOKEN2 = os.getenv("TOKEN2")
if not TOKEN2:
    raise RuntimeError("TOKEN2 .env dosyasında eksik!")

GUILD_ID = int(os.getenv("GUILD_ID", 0) or 0)
if not GUILD_ID:
    raise RuntimeError("GUILD_ID .env dosyasında eksik!")

YETKILI_KOMUT_KANALI = int(os.getenv("YETKILI_KOMUT_KANALI", 0) or 0)

# Roller
ROL_SORUMLUSU = int(os.getenv("ROL_SORUMLUSU", 0) or 0)
LIDER = int(os.getenv("LIDER", 0) or 0)
TUM_YETKILILER = [int(x) for x in os.getenv("TUM_YETKILILER", "").split(",") if x.strip().isdigit()]
SES_SORUMLUSU = int(os.getenv("SES_SORUMLUSU", 0) or 0)
CHAT_SORUMLUSU = int(os.getenv("CHAT_SORUMLUSU", 0) or 0)
KAYIT_SORUMLUSU = int(os.getenv("KAYIT_SORUMLUSU", 0) or 0)

MUTE_ROL = int(os.getenv("MUTE_ROL", 0) or 0)
REKLAM_ROL = int(os.getenv("REKLAM_ROL", 0) or 0)
YAYINCI_ROL = int(os.getenv("YAYINCI_ROL", 0) or 0)

NOVA_UYE = int(os.getenv("NOVA_UYE", 0) or 0)
ERKEK = int(os.getenv("ERKEK", 0) or 0)
KIZ = int(os.getenv("KIZ", 0) or 0)

# Kanallar
SES_KANALLARI = [int(x) for x in os.getenv("SES_KANALLARI", "").split(",") if x.strip().isdigit()]
CHAT_KANALLARI = [int(x) for x in os.getenv("CHAT_KANALLARI", "").split(",") if x.strip().isdigit()]
KOMUT_KANALLARI = [int(x) for x in os.getenv("KOMUT_KANALLARI", "").split(",") if x.strip().isdigit()]
SES_KOMUT_KANALLARI = [int(x) for x in os.getenv("SES_KOMUT_KANALLARI", "").split(",") if x.strip().isdigit()]

DB_FILE = "data.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"mute": {}, "ses": {}, "ses_giris": {}, "chat": {}, "komut": {}}, f, indent=2, ensure_ascii=False)

# ----------------------------------------
# INTENTS & BOT
# ----------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)
db_lock = asyncio.Lock()


# ----------------------------------------
# DB UTILS
# ----------------------------------------
def load_db():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def safe_load_db():
    async with db_lock:
        return load_db()


async def safe_save_db(data):
    async with db_lock:
        save_db(data)


# ----------------------------------------
# EMOJİ & RENKLER
# ----------------------------------------
EMOJI = {
    "success": "Success", "error": "Error", "warning": "Warning", "info": "Info",
    "loading": "Loading", "mute": "Muted", "unmute": "Unmuted", "ban": "Banned",
    "unban": "Unbanned", "role": "Role", "voice": "Voice", "chat": "Chat",
    "command": "Command", "trash": "Trash", "pull": "Pull", "dm": "DM",
    "stats": "Stats", "clear": "Clear", "confirm": "Confirm", "cancel": "Cancel"
}
COLOR = {
    "success": 0x57F287, "error": 0xED4245, "warning": 0xFEE75C,
    "info": 0x5865F2, "neutral": 0x2F3136
}


# ----------------------------------------
# ANIMATED EMBED & PROGRESS
# ----------------------------------------
async def loading_embed(channel, title="İşlem Yapılıyor", desc="Lütfen bekleyin..."):
    msg = await channel.send(
        embed=discord.Embed(title=f"{EMOJI['loading']} {title}", description=desc, color=COLOR["info"]))
    return msg


async def update_progress(msg, current, total, action="Gönderiliyor"):
    percent = int((current / total) * 100)
    bar = "█" * int(percent // 5) + "░" * (20 - int(percent // 5))
    await msg.edit(embed=discord.Embed(
        title=f"{EMOJI['loading']} {action}",
        description=f"**[{bar}] {percent}%**\n`{current}/{total}` tamamlandı.",
        color=COLOR["info"]
    ))


def make_embed(title="", description="", color=COLOR["neutral"], footer=None, thumb=None):
    e = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    if footer: e.set_footer(text=footer)
    if thumb: e.set_thumbnail(url=thumb)
    return e


# ----------------------------------------
# ESNEK KANAL + YETKİ KONTROLÜ
# ----------------------------------------
def kanal_ve_yetki_kontrolu(gerekli_roller=None, izinli_kanallar=None):
    if gerekli_roller is None: gerekli_roller = []
    if izinli_kanallar is None: izinli_kanallar = []

    async def predicate(ctx):
        if izinli_kanallar and ctx.channel.id not in izinli_kanallar:
            kanallar = ", ".join(f"<#{k}>" for k in izinli_kanallar)
            await send_temp(ctx, "error", "Yanlış Kanal", f"Bu komut sadece şu kanallarda kullanılabilir:\n{kanallar}")
            return False

        user_roles = [r.id for r in ctx.author.roles]
        if not any(r in gerekli_roller for r in user_roles):
            roller = [ctx.guild.get_role(r).name if ctx.guild.get_role(r) else "Silinmiş Rol" for r in gerekli_roller]
            await send_temp(ctx, "error", "Yetki Yok", f"Gerekli roller: {', '.join(roller)}")
            return False

        return True

    return commands.check(predicate)


# ----------------------------------------
# HELPERS
# ----------------------------------------
async def send_temp(channel, type_, title, description, delete_after=7, author=None):
    color = COLOR[type_]
    emoji = EMOJI[type_]
    footer = f"Yetkili: {author}" if author else None
    msg = await channel.send(embed=make_embed(f"{emoji} {title}", description, color, footer=footer))
    if delete_after:
        await asyncio.sleep(delete_after)
        try:
            await msg.delete()
        except:
            pass


# ----------------------------------------
# CONFIRM VIEW
# ----------------------------------------
class ConfirmView(discord.ui.View):
    def __init__(self, ctx, timeout=30):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.result = None

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.danger, emoji="Confirm")
    async def confirm(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Bu buton sana ait değil!", ephemeral=True)
        self.result = True
        self.stop()
        await interaction.response.edit_message(content=f"{EMOJI['success']} Onaylandı!", embed=None, view=None)

    @discord.ui.button(label="İptal Et", style=discord.ButtonStyle.secondary, emoji="Cancel")
    async def cancel(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Bu buton sana ait değil!", ephemeral=True)
        self.result = False
        self.stop()
        await interaction.response.edit_message(content=f"{EMOJI['cancel']} İptal edildi.", embed=None, view=None)


# ----------------------------------------
# YAYIN İZNİ KONTROL FONKSİYONU
# ----------------------------------------
async def kontrol_yayin_izni(member, channel):
    if not YAYINCI_ROL:
        return
    yayinci_role = member.guild.get_role(YAYINCI_ROL)
    if not yayinci_role:
        return

    # Yayıncı rolüne stream izni ver
    await channel.set_permissions(yayinci_role, stream=True)
    # @everyone'a stream iznini kaldır
    await channel.set_permissions(member.guild.default_role, stream=False)

    # Diğer rollerden stream iznini kaldır
    for role in member.roles:
        if role == member.guild.default_role or role == yayinci_role:
            continue
        perms = channel.overwrites_for(role)
        if perms.stream is True:
            perms.stream = False
            await channel.set_permissions(role, overwrite=perms)


# ----------------------------------------
# .yetki KOMUTU (SAYFALAMA)
# ----------------------------------------
class RolePaginator(discord.ui.View):
    def __init__(self, ctx, roles, target_member):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.roles = roles
        self.target = target_member
        self.page = 0
        self.per_page = 10

    async def update(self, interaction=None):
        start = self.page * self.per_page
        end = start + self.per_page
        page_roles = self.roles[start:end]

        options = [discord.SelectOption(label=r.name, value=str(r.id)) for r in page_roles]
        select = discord.ui.Select(placeholder="Rol seç...", options=options, min_values=1, max_values=len(options))
        select.callback = self.select_callback
        self.clear_items()
        self.add_item(select)

        if self.page > 0:
            prev = discord.ui.Button(label="Önceki", style=discord.ButtonStyle.secondary)
            prev.callback = self.prev_page
            self.add_item(prev)
        if end < len(self.roles):
            next_btn = discord.ui.Button(label="Sonraki", style=discord.ButtonStyle.secondary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)

        embed = make_embed(
            title=f"{EMOJI['role']} Rol Seçimi • Sayfa {self.page + 1}",
            description=f"{self.target.mention} için rol seçin:\n`{len(self.roles)} rol mevcut`",
            color=COLOR["info"]
        )
        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.ctx.send(embed=embed, view=self)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Bu menüyü sen açmadın!", ephemeral=True)
        selected = [self.ctx.guild.get_role(int(v)) for v in interaction.data["values"]]
        await self.target.add_roles(*selected, reason=f"Yetki: {self.ctx.author}")
        await interaction.response.edit_message(
            content=f"{EMOJI['success']} **{len(selected)} rol** {self.target.mention} kullanıcısına verildi!",
            embed=None, view=None
        )

    async def prev_page(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        await self.update(interaction)

    async def next_page(self, interaction: discord.Interaction):
        self.page = min((len(self.roles) - 1) // self.per_page, self.page + 1)
        await self.update(interaction)


@bot.command(name="yetki")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=[ROL_SORUMLUSU, LIDER],
    izinli_kanallar=[YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else []
)
async def yetki_ver(ctx: commands.Context, uye: discord.Member):
    roles = [r for r in ctx.guild.roles if r != ctx.guild.default_role and r < ctx.guild.me.top_role and not r.managed]
    if not roles:
        return await send_temp(ctx, "error", "Rol Yok", "Botun üstünde rol yok!")
    roles = sorted(roles, key=lambda x: x.position, reverse=True)
    view = RolePaginator(ctx, roles, uye)
    await view.update()


# ----------------------------------------
# .mute
# ----------------------------------------
@bot.command(name="mute")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=TUM_YETKILILER + [ROL_SORUMLUSU, LIDER],
    izinli_kanallar=(
            [YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else [] +
                                                                KOMUT_KANALLARI + SES_KOMUT_KANALLARI
    )
)
async def mute(ctx, uye: discord.Member, dakika: int):
    if dakika <= 0: return await send_temp(ctx, "error", "Geçersiz Süre", "Dakika pozitif olmalı!")
    if MUTE_ROL == 0: return await send_temp(ctx, "error", "Ayar Eksik", "MUTE_ROL .env'de eksik!")
    mute_role = ctx.guild.get_role(MUTE_ROL)
    if not mute_role: return await send_temp(ctx, "error", "Rol Yok", "Mute rolü bulunamadı!")
    if mute_role in uye.roles: return await send_temp(ctx, "info", "Zaten Muteli", f"{uye.mention} zaten susturulmuş.")

    try:
        for channel in ctx.guild.text_channels:
            await channel.set_permissions(mute_role, send_messages=False, add_reactions=False)
        for channel in ctx.guild.voice_channels:
            await channel.set_permissions(mute_role, speak=False, stream=False, use_voice_activation=False)
    except Exception as e:
        print(f"Mute izinleri ayarlanamadı: {e}")

    await uye.add_roles(mute_role, reason=f"Mute: {ctx.author} | {dakika} dk")
    async with db_lock:
        db = load_db()
        db["mute"][str(uye.id)] = datetime.now().timestamp() + (dakika * 60)
        save_db(db)

    await send_temp(ctx, "success", "Susturuldu!",
                    f"{uye.mention} **{dakika} dakika** boyunca **yazamaz ve konuşamaz**.", author=ctx.author)


@bot.command(name="unmute")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=[ROL_SORUMLUSU, LIDER],
    izinli_kanallar=[YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else []
)
async def unmute(ctx, uye: discord.Member):
    mute_role = ctx.guild.get_role(MUTE_ROL)
    if not mute_role or mute_role not in uye.roles:
        return await send_temp(ctx, "info", "Muteli Değil", f"{uye.mention} zaten konuşabiliyor.")
    await uye.remove_roles(mute_role, reason=f"Unmute: {ctx.author}")
    async with db_lock:
        db = load_db()
        db["mute"].pop(str(uye.id), None)
        save_db(db)
    await send_temp(ctx, "success", "Sesi Açıldı!", f"{uye.mention} artık yazabilir ve konuşabilir.", author=ctx.author)


# ----------------------------------------
# .reklam → YAYINCI ROLÜ DE KALDIRILIYOR!
# ----------------------------------------
@bot.command(name="reklam")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=TUM_YETKILILER + [ROL_SORUMLUSU, LIDER],
    izinli_kanallar=(
            [YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else [] +
                                                                KOMUT_KANALLARI + SES_KOMUT_KANALLARI
    )
)
async def reklam(ctx, uye: discord.Member, *, sebep: str = "Belirtilmedi"):
    if not all([REKLAM_ROL, ERKEK, KIZ]):
        return await send_temp(ctx, "error", "Ayar Eksik", "`.env`'de `REKLAM_ROL`, `ERKEK`, `KIZ` eksik!")
    reklam_role = ctx.guild.get_role(REKLAM_ROL)
    erkek_role = ctx.guild.get_role(ERKEK)
    kiz_role = ctx.guild.get_role(KIZ)
    yayinci_role = ctx.guild.get_role(YAYINCI_ROL) if YAYINCI_ROL else None

    if not all([reklam_role, erkek_role, kiz_role]):
        return await send_temp(ctx, "error", "Rol Bulunamadı", "Reklam, Erkek veya Kız rolü yok!")

    cinsiyet_role = erkek_role if erkek_role in uye.roles else (kiz_role if kiz_role in uye.roles else None)
    if not cinsiyet_role:
        return await send_temp(ctx, "error", "Cinsiyet Eksik",
                               f"{uye.mention} **Erkek** veya **Kız** rolüne sahip değil!")

    kalacak_roller = {cinsiyet_role, reklam_role}
    kaldirilacak_roller = [
        r for r in uye.roles
        if
        r != ctx.guild.default_role and r not in kalacak_roller and not r.permissions.administrator and r < ctx.guild.me.top_role
    ]

    if yayinci_role and yayinci_role in uye.roles:
        kaldirilacak_roller.append(yayinci_role)

    if not kaldirilacak_roller and reklam_role in uye.roles:
        return await send_temp(ctx, "info", "Zaten Ceza", f"{uye.mention} zaten reklam cezası almış.")

    progress = await loading_embed(ctx.channel, "Reklam Cezası Uygulanıyor...")
    try:
        if kaldirilacak_roller:
            await uye.remove_roles(*kaldirilacak_roller, reason=f"Reklam: {ctx.author} | {sebep}")
        await uye.add_roles(cinsiyet_role, reklam_role, reason=f"Reklam: {ctx.author} | {sebep}")
        await update_progress(progress, 1, 1, "Tamamlandı")
        await asyncio.sleep(1)
        await progress.edit(
            content=None,
            embed=make_embed(
                title=f"{EMOJI['warning']} Reklam Cezası!",
                description=f"**{uye.mention}** cezalandırıldı.\n**Sebep:** {sebep}\n**Kalan:** {cinsiyet_role.mention}, {reklam_role.mention}\n**Yayıncı rolü de kaldırıldı!**",
                color=COLOR["warning"],
                footer=f"Yetkili: {ctx.author}"
            ).set_thumbnail(url=uye.display_avatar.url)
        )
    except discord.Forbidden:
        await progress.edit(content=f"{EMOJI['error']} Yetki yetersiz!")
    except Exception as e:
        await progress.edit(content=f"{EMOJI['error']} Hata: {e}")


# ----------------------------------------
# .ban / .unban
# ----------------------------------------
@bot.command(name="ban")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=TUM_YETKILILER + [ROL_SORUMLUSU, LIDER],
    izinli_kanallar=(
            [YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else [] +
                                                                KOMUT_KANALLARI + SES_KOMUT_KANALLARI
    )
)
async def ban(ctx, uye: discord.Member, *, sebep="Belirtilmedi"):
    view = ConfirmView(ctx)
    msg = await ctx.send(
        embed=make_embed(f"{EMOJI['ban']} Ban Onayı", f"{uye.mention} banlansın mı?\n**Sebep:** {sebep}",
                         COLOR["warning"]), view=view)
    await view.wait()
    if not view.result: return
    await uye.ban(reason=f"{ctx.author}: {sebep}")
    await msg.edit(content=f"{EMOJI['ban']} **{uye} banlandı!**", embed=None, view=None)


@bot.command(name="unban")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=TUM_YETKILILER + [ROL_SORUMLUSU, LIDER],
    izinli_kanallar=[YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else []
)
async def unban(ctx, uye_id: int, *, sebep="Belirtilmedi"):
    try:
        user = await bot.fetch_user(uye_id)
        await ctx.guild.unban(user, reason=f"{ctx.author}: {sebep}")
        await send_temp(ctx, "success", "Ban Kaldırıldı", f"`{user}` artık dönebilir.", author=ctx.author)
    except discord.NotFound:
        await send_temp(ctx, "error", "Bulunamadı", "Kullanıcı banlı değil.")


# ----------------------------------------
# .mesaj
# ----------------------------------------
@bot.command(name="mesaj")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=[ROL_SORUMLUSU, LIDER],
    izinli_kanallar=[YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else []
)
async def mesaj_gonder(ctx, rol: discord.Role, *, mesaj):
    members = [m for m in rol.members if not m.bot]
    if not members: return await send_temp(ctx, "info", "Boş Rol", "Bu rolde kimse yok.")
    progress = await loading_embed(ctx.channel, f"DM Gönderiliyor → {rol.name}")
    sent = failed = 0
    for i, m in enumerate(members, 1):
        try:
            await m.send(f"**{rol.name}** → {mesaj}")
            sent += 1
        except:
            failed += 1
        if i % 5 == 0 or i == len(members):
            await update_progress(progress, sent + failed, len(members), "DM Gönderiliyor")
            await asyncio.sleep(0.5)
    await progress.edit(content=f"{EMOJI['dm']} **{sent}** gönderildi, **{failed}** başarısız.", embed=None)


# ----------------------------------------
# .detay
# ----------------------------------------
@bot.command(name="detay")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=TUM_YETKILILER + [ROL_SORUMLUSU, LIDER],
    izinli_kanallar=(
            [YETKILI_KOMUT_KANALI] if YETKILI_KOMUT_KANALI else [] +
                                                                KOMUT_KANALLARI + SES_KOMUT_KANALLARI
    )
)
async def detay(ctx, uye: discord.Member = None, gun: int = 7):
    if gun not in range(1, 31): return await send_temp(ctx, "error", "Gün Aralığı", "1-30 gün arası girin.")
    uye = uye or ctx.author
    now = datetime.now().timestamp()
    saniye = gun * 86400
    db = await safe_load_db()
    ses = sum(float(v) for k, v in db.get("ses", {}).get(str(uye.id), {}).items() if now - float(k) <= saniye) / 3600
    mesaj = sum(int(v) for k, v in db.get("chat", {}).get(str(uye.id), {}).items() if now - float(k) <= saniye)
    komut = sum(int(v) for k, v in db.get("komut", {}).get(str(uye.id), {}).items() if now - float(k) <= saniye)
    embed = make_embed(f"{EMOJI['stats']} {uye.display_name} • Son {gun} Gün", color=COLOR["info"])
    embed.set_thumbnail(url=uye.display_avatar.url)
    embed.add_field(name=f"{EMOJI['voice']} Ses", value=f"**{round(ses, 2)} saat**", inline=True)
    embed.add_field(name=f"{EMOJI['chat']} Mesaj", value=f"**{mesaj}**", inline=True)
    embed.add_field(name=f"{EMOJI['command']} Komut", value=f"**{komut}**", inline=True)
    embed.set_footer(text=f"İsteyen: {ctx.author}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)


# ----------------------------------------
# .çek
# ----------------------------------------
@bot.command(name="çek")
@kanal_ve_yetki_kontrolu(
    gerekli_roller=TUM_YETKILILER + [ROL_SORUMLUSU, LIDER, SES_SORUMLUSU],
    izinli_kanallar=SES_KOMUT_KANALLARI
)
async def cek(ctx, hedef: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await send_temp(ctx, "error", "Ses Kanalı", "Sen ses kanalında değilsin!")
    if not hedef.voice or not hedef.voice.channel:
        return await send_temp(ctx, "error", "Hedef", "Hedef kullanıcı ses kanalında değil!")
    await hedef.move_to(ctx.author.voice.channel, reason=f"Çek: {ctx.author}")
    await send_temp(ctx, "success", "Çekildi!", f"{hedef.mention} → {ctx.author.voice.channel.mention}",
                    author=ctx.author)


# ----------------------------------------
# .yayıncı + KISALTMALAR (.yt, .yayın) - SADECE SES KOMUT KANALLARINDA
# ----------------------------------------
@bot.command(name="yayıncı", aliases=["yt", "yayın"])
@kanal_ve_yetki_kontrolu(
    gerekli_roller=[ROL_SORUMLUSU, LIDER, SES_SORUMLUSU],
    izinli_kanallar=SES_KOMUT_KANALLARI
)
async def yayinci_ver(ctx, uye: discord.Member):
    if not YAYINCI_ROL:
        return await send_temp(ctx, "error", "Ayar Eksik", "YAYINCI_ROL .env'de eksik!")
    role = ctx.guild.get_role(YAYINCI_ROL)
    if not role:
        return await send_temp(ctx, "error", "Rol Yok", "Yayıncı rolü bulunamadı!")

    voice_channel = uye.voice.channel if uye.voice and uye.voice.channel else None

    if role in uye.roles:
        await uye.remove_roles(role, reason=f"Yayıncı rolü alındı: {ctx.author}")
        await send_temp(ctx, "success", "Rol Alındı", f"{uye.mention}'dan **Yayıncı** rolü alındı.", author=ctx.author)
    else:
        await uye.add_roles(role, reason=f"Yayıncı rolü verildi: {ctx.author}")
        await send_temp(ctx, "success", "Rol Verildi", f"{uye.mention} artık **Yayıncı**!", author=ctx.author)

    # İzinleri güncelle
    if voice_channel and voice_channel.id in SES_KANALLARI:
        await kontrol_yayin_izni(uye, voice_channel)
    else:
        for ch in ctx.guild.voice_channels:
            if ch.id in SES_KANALLARI:
                await kontrol_yayin_izni(uye, ch)


# ----------------------------------------
# GÜVENLİK: SADECE 1 SUNUCUYA İZİN
# ----------------------------------------
@bot.event
async def on_ready():
    print(f"{bot.user} aktif! | {len(bot.guilds)} sunucu")

    # Sadece izinli sunucuda çalış
    izinli_sunucu = bot.get_guild(GUILD_ID)
    if not izinli_sunucu:
        print(f"[GÜVENLİK] Bot, izinli sunucuda değil! Çıkılıyor...")
        await bot.close()
        return

    # Diğer sunuculardan çık
    cikan = 0
    for guild in bot.guilds:
        if guild.id != GUILD_ID:
            try:
                await guild.leave()
                print(f"[GÜVENLİK] {guild.name} ({guild.id}) sunucusundan çıkıldı.")
                cikan += 1
            except:
                pass

    if cikan > 0:
        print(f"[GÜVENLİK] Toplam {cikan} yetkisiz sunucudan çıkıldı.")

    print(f"[GÜVENLİK] Sadece izinli sunucuda aktif: {izinli_sunucu.name}")

    if not check_unmutes_loop.is_running():
        check_unmutes_loop.start()

    # Yayın izinlerini ayarla
    if YAYINCI_ROL:
        yayinci_role = izinli_sunucu.get_role(YAYINCI_ROL)
        if yayinci_role:
            for channel in izinli_sunucu.voice_channels:
                if channel.id in SES_KANALLARI:
                    try:
                        await channel.set_permissions(yayinci_role, stream=True)
                        await channel.set_permissions(izinli_sunucu.default_role, stream=False)
                    except:
                        pass


@bot.event
async def on_guild_join(guild):
    if guild.id != GUILD_ID:
        try:
            await guild.leave()
            print(f"[GÜVENLİK] Yetkisiz sunucudan çıkıldı: {guild.name} ({guild.id})")
        except:
            pass


# ----------------------------------------
# YAYIN AÇMA KONTROLÜ + İZİN GÜNCELLEME
# ----------------------------------------
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot: return

    # Yayın açma kontrolü (ekstra güvenlik)
    if after.self_stream and not before.self_stream:
        if not YAYINCI_ROL:
            try:
                await member.edit(stream=False)
                await member.send(embed=make_embed(
                    title="Yayın İzni Yok!",
                    description="Bu sunucuda yayın açmak **yasak**!\nSadece **Yayıncı** rolü olanlar açabilir.",
                    color=COLOR["error"]
                ))
            except:
                pass
            return

        role = member.guild.get_role(YAYINCI_ROL)
        if not role or role not in member.roles:
            try:
                await member.edit(stream=False)
                await member.send(embed=make_embed(
                    title="Yayın İzni Yok!",
                    description="Yayın açabilmek için **Yayıncı** rolüne sahip olmalısın!\n`.yt @kullanıcı` ile yetkiliye söyle.",
                    color=COLOR["error"]
                ))
            except:
                pass
            return

    # İzin güncelleme
    if after.channel and after.channel.id in SES_KANALLARI:
        await kontrol_yayin_izni(member, after.channel)

    # Ses takibi
    db = await safe_load_db()
    now = datetime.now().timestamp()
    if before.channel is None and after.channel and after.channel.id in SES_KANALLARI:
        db["ses_giris"][str(member.id)] = now
    elif before.channel and after.channel is None and before.channel.id in SES_KANALLARI:
        giris = db["ses_giris"].pop(str(member.id), None)
        if giris:
            sure = now - giris
            db["ses"].setdefault(str(member.id), {})[str(int(giris))] = sure
    await safe_save_db(db)


# ----------------------------------------
# MESAJ TAKİP VE KOMUT SAYACI
# ----------------------------------------
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    db = await safe_load_db()
    now = datetime.now().timestamp()
    ts = str(int(now // 3600))

    if msg.content.startswith(".") and msg.channel.id in KOMUT_KANALLARI:
        db.setdefault("komut", {}).setdefault(str(msg.author.id), {}).setdefault(ts, 0)
        db["komut"][str(msg.author.id)][ts] += 1

    if msg.channel.id in CHAT_KANALLARI:
        db.setdefault("chat", {}).setdefault(str(msg.author.id), {}).setdefault(ts, 0)
        db["chat"][str(msg.author.id)][ts] += 1

    await safe_save_db(db)
    await bot.process_commands(msg)


# ----------------------------------------
# MUTE SÜRESİ KONTROLÜ
# ----------------------------------------
@tasks.loop(seconds=15)
async def check_unmutes_loop():
    db = await safe_load_db()
    now = datetime.now().timestamp()
    changed = False
    for uid, ts in list(db.get("mute", {}).items()):
        if now >= ts:
            guild = bot.get_guild(GUILD_ID)
            if guild:
                member = guild.get_member(int(uid))
                if member and MUTE_ROL:
                    role = guild.get_role(MUTE_ROL)
                    if role and role in member.roles:
                        await member.remove_roles(role, reason="Süre doldu")
            db["mute"].pop(uid, None)
            changed = True
    if changed: await safe_save_db(db)


@check_unmutes_loop.before_loop
async def before_unmutes():
    await bot.wait_until_ready()


# ----------------------------------------
# HATA YÖNETİMİ
# ----------------------------------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await send_temp(ctx, "error", "Eksik", f"`{error.param.name}` eksik!")
    elif isinstance(error, commands.BadArgument):
        await send_temp(ctx, "error", "Geçersiz", "Doğru formatta girin.")
    elif isinstance(error, commands.CheckFailure):
        await send_temp(ctx, "error", "Yetki", str(error))
    else:
        print(f"Hata: {error}")
        await send_temp(ctx, "error", "Hata", "Konsola bakın.")


# ----------------------------------------
# RUN
# ----------------------------------------
if __name__ == "__main__":
    bot.run(TOKEN2)