# kayıt.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timezone

# ========================================
# .env YÜKLEME
# ========================================
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN .env dosyasında eksik!")

# Roller (Güvenli okuma)
def get_role(env_name):
    val = os.getenv(env_name)
    return int(val) if val and val.isdigit() else 0

NOVA_LIDER = get_role("NOVA_LIDER")
KAYIT_SORUMLUSU = get_role("KAYIT_SORUMLUSU")
KAYITSIZ = get_role("KAYITSIZ")
NOVA_UYE = get_role("NOVA_UYE")
ERKEK = get_role("ERKEK")
KIZ = get_role("KIZ")

# Kanallar
HOSGELDIN_KANALI = int(os.getenv("HOSGELDIN_KANALI", 0))
KAYIT_KANALI = int(os.getenv("KAYIT_KANALI", 0))

# ========================================
# INTENTS
# ========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# ========================================
# KOMUT KANAL KONTROLÜ
# ========================================
def kanal_kontrol():
    async def predicate(ctx):
        if KAYIT_KANALI == 0:
            return True
        if ctx.channel.id != KAYIT_KANALI:
            await ctx.send(f"Bu komut sadece <#{KAYIT_KANALI}> kanalında kullanılabilir!")
            return False
        return True
    return commands.check(predicate)

# ========================================
# 1) Yeni Üye → İSİM: "İsim | Yaş" → MESAJ: <@ID>
# ========================================
@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        return

    guild = member.guild
    uye_sayisi = guild.member_count

    # HESAP YAŞI – SADECE VAR OLAN BİRİMLER
    olusturulma = member.created_at
    su_an = datetime.now(timezone.utc)
    fark = su_an - olusturulma

    yil = fark.days // 365
    kalan_gun = fark.days % 365
    ay = kalan_gun // 30
    gun = kalan_gun % 30

    yas_parcalar = []
    if yil > 0:
        yas_parcalar.append(f"{yil} YIL")
    if ay > 0:
        yas_parcalar.append(f"{ay} AY")
    if gun > 0:
        yas_parcalar.append(f"{gun} GÜN")
    if not yas_parcalar:
        yas_parcalar.append("0 GÜN")

    yas_metni = " | ".join(yas_parcalar)

    # Tarih formatı
    aylar = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    gun_isimleri = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

    tarih_str = f"{olusturulma.day} {aylar[olusturulma.month]} {olusturulma.year} {gun_isimleri[olusturulma.weekday()]} {olusturulma.strftime('%H:%M')}"

    # 1) İSİM: "İsim | Yaş" → LİTERAL
    yeni_isim = "İsim | Yaş"

    try:
        await member.edit(nick=yeni_isim, reason="Yeni üye → İsim: İsim | Yaş")
        print(f"[BAŞARILI] {member} → İsim: {yeni_isim}")
    except discord.Forbidden:
        print(f"[HATA] {member} → İsim değiştirilemedi: Yetki eksik!")
    except Exception as e:
        print(f"[HATA] İsim değiştirme hatası: {e}")

    # 2) KAYITSIZ ROLÜ VER
    if KAYITSIZ == 0:
        print(f"[UYARI] KAYITSIZ rol ID'si .env'de eksik!")
    else:
        kayitsiz_rol = guild.get_role(KAYITSIZ)
        if not kayitsiz_rol:
            print(f"[HATA] KAYITSIZ rolü (ID: {KAYITSIZ}) sunucuda yok!")
        else:
            try:
                await member.add_roles(kayitsiz_rol, reason="Yeni üye → Kayıtsız")
                print(f"[BAŞARILI] {member} → Kayıtsız rolü VERİLDİ.")
            except discord.Forbidden:
                print(f"[HATA] {member} → Kayıtsız rolü verilemedi: Yetki eksik!")
            except Exception as e:
                print(f"[HATA] Kayıtsız rolü hatası: {e}")

    # 3) HOŞ GELDİN MESAJI → <@ID> İLE
    if HOSGELDIN_KANALI != 0:
        kanal = guild.get_channel(HOSGELDIN_KANALI)
        if kanal:
            try:
                hosgeldin = (
                    f"<@{member.id}>, **DARK NOVA** Sunucumuza Hoş Geldin. "
                    f"Seninle birlikte sunucumuz **{uye_sayisi}** üye sayısına ulaştı. "
                    f"Hesabın **{yas_metni}** önce **{tarih_str}** tarihinde oluşturulmuş. "
                    f"**NOVA SES ¹** Kanalına katılarak \"İsim | Yaş\" vererek kayıt olabilirsiniz. "
                    f"Takviye yaparak bize destek olabilirsiniz. <@&{KAYIT_SORUMLUSU}> "
                    f"**Kayıt olduktan sonra kuralları okuduğunuzu kabul edeceğiz ve içeride yapılacak cezalandırma işlemlerini bunu göz önünde bulundurarak yapacağız.**"
                )
                await kanal.send(hosgeldin)
                print(f"[HOŞ GELDİN] <@{member.id}> → Mesaj gönderildi.")
            except Exception as e:
                print(f"[HATA] Hoş geldin mesajı gönderilemedi: {e}")

# ========================================
# 2) .k Komutu
# ========================================
@bot.command(name="k")
@kanal_kontrol()
async def kayit_baslat(ctx: commands.Context, uye: discord.Member, isim: str, yas: int, cinsiyet: str):
    await kayit_islemi(ctx, uye, isim, yas, cinsiyet, kayitsiz_kontrol=True)

# ========================================
# 3) .isim Komutu
# ========================================
@bot.command(name="isim")
@kanal_kontrol()
async def isim_guncelle(ctx: commands.Context, uye: discord.Member, isim: str, yas: int, cinsiyet: str):
    await kayit_islemi(ctx, uye, isim, yas, cinsiyet, kayitsiz_kontrol=False)

# ========================================
# 4) .ksil Komutu – KAYIT SIFIRLA
# ========================================
@bot.command(name="ksil")
@kanal_kontrol()
async def kayit_sil(ctx: commands.Context, uye_id: int):
    # Yetki kontrolü
    if ctx.author.id == ctx.guild.owner_id:
        pass
    elif NOVA_LIDER != 0 and NOVA_LIDER in [r.id for r in ctx.author.roles]:
        pass
    elif KAYIT_SORUMLUSU != 0 and KAYIT_SORUMLUSU in [r.id for r in ctx.author.roles]:
        pass
    else:
        return await ctx.send("Bu komutu sadece yetkili kullanabilir!")

    uye = ctx.guild.get_member(uye_id)
    if not uye:
        return await ctx.send("Bu ID'ye sahip üye sunucuda bulunamadı!")

    if KAYITSIZ == 0:
        return await ctx.send("**KAYITSIZ** rolü `.env`'de tanımlı değil!")

    kayitsiz = ctx.guild.get_role(KAYITSIZ)
    if not kayitsiz:
        return await ctx.send("**KAYITSIZ** rolü sunucuda yok!")

    try:
        await uye.remove_roles(*uye.roles, reason="Kayıt sıfırlandı")
        await uye.add_roles(kayitsiz, reason="Kayıt sıfırlandı → Kayıtsız")

        yeni_isim = "İsim | Yaş"
        await uye.edit(nick=yeni_isim, reason="Kayıt sıfırlandı → İsim: İsim | Yaş")

        embed = discord.Embed(
            title="Kayıt Sıfırlandı!",
            description=f"{uye.mention} kullanıcısının kaydı tamamen sıfırlandı.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Yeni İsim", value=yeni_isim, inline=True)
        embed.add_field(name="Yeni Rol", value=f"<@&{KAYITSIZ}>", inline=True)
        embed.set_footer(text="NOVA Ailesi")
        await ctx.send(embed=embed)

        print(f"[BAŞARILI] {uye} → Kayıt sıfırlandı: {yeni_isim}")

    except discord.Forbidden:
        await ctx.send("Botun yetkisi yok! Rol hiyerarşisi veya isim değiştirme izni eksik.")
    except Exception as e:
        await ctx.send("Hata oluştu.")
        print(f"[HATA] .ksil: {e}")

# ========================================
# 5) .sil Komutu – MESAJ SİLME (YENİ)
# ========================================
@bot.command(name="sil")
@commands.has_permissions(manage_messages=True)
async def sil_mesaj(ctx: commands.Context, arg: str = None):
    if arg is None:
        return await ctx.send("Kullanım: `.sil <sayı>` veya `.sil clear`")

    try:
        if arg.lower() == "clear":
            # TÜM MESAJLARI SİL (Discord 100 mesaj sınırı var, döngü ile)
            silinen = 0
            async for _ in ctx.channel.history(limit=None):
                await ctx.channel.purge(limit=100)
                silinen += 100
            await ctx.send(f"**{silinen}+ mesaj silindi.**", delete_after=3)
            print(f"[SİL] {ctx.author} → clear: {silinen}+ mesaj")
        else:
            sayi = int(arg)
            if sayi <= 0:
                return await ctx.send("Pozitif bir sayı girin!")
            if sayi > 100:
                return await ctx.send("Maksimum 100 mesaj silebilirim!")

            await ctx.channel.purge(limit=sayi + 1)  # +1 kendi mesajı
            await ctx.send(f"**{sayi} mesaj silindi.**", delete_after=3)
            print(f"[SİL] {ctx.author} → {sayi} mesaj silindi.")
    except ValueError:
        await ctx.send("Geçerli bir sayı veya `clear` yazın!")
    except discord.Forbidden:
        await ctx.send("Mesaj silme yetkim yok!")
    except Exception as e:
        await ctx.send("Hata oluştu.")
        print(f"[HATA] .sil: {e}")

# ========================================
# 6) Ortak Kayıt Fonksiyonu
# ========================================
async def kayit_islemi(ctx: commands.Context, uye: discord.Member, isim: str, yas: int, cinsiyet: str, kayitsiz_kontrol: bool):
    # Yetki kontrolü
    if ctx.author.id == ctx.guild.owner_id:
        pass
    elif NOVA_LIDER != 0 and NOVA_LIDER in [r.id for r in ctx.author.roles]:
        pass
    elif KAYIT_SORUMLUSU != 0 and KAYIT_SORUMLUSU in [r.id for r in ctx.author.roles]:
        pass
    else:
        return await ctx.send("Bu komutu sadece yetkili kullanabilir!")

    # Kayıtsız kontrol
    kayitsiz_var = KAYITSIZ != 0 and KAYITSIZ in [r.id for r in uye.roles]

    if kayitsiz_kontrol:
        if not kayitsiz_var:
            return await ctx.send("Bu kullanıcı zaten kayıtlı!")
    else:
        if NOVA_UYE == 0 or NOVA_UYE not in [r.id for r in uye.roles]:
            return await ctx.send("Bu kullanıcı kayıtlı değil!")

    # Cinsiyet kontrolü
    cinsiyet = cinsiyet.strip().lower()
    if cinsiyet not in ["erkek", "kız", "erke", "kiz"]:
        return await ctx.send("Cinsiyet **ERKEK** veya **KIZ** olmalı!")

    rol_id = ERKEK if cinsiyet.startswith("erk") else KIZ
    cinsiyet_rol = ctx.guild.get_role(rol_id)
    nova_uye = ctx.guild.get_role(NOVA_UYE)
    kayitsiz = ctx.guild.get_role(KAYITSIZ)

    if not nova_uye:
        return await ctx.send("**NOVA_UYE** rolü sunucuda yok!")
    if not cinsiyet_rol:
        return await ctx.send(f"**{cinsiyet.upper()}** rolü sunucuda yok!")
    if kayitsiz_kontrol and not kayitsiz:
        return await ctx.send("**KAYITSIZ** rolü sunucuda yok!")

    try:
        if kayitsiz_var and kayitsiz:
            await uye.remove_roles(kayitsiz, reason="Kayıt tamamlandı")

        if NOVA_UYE not in [r.id for r in uye.roles]:
            await uye.add_roles(nova_uye, reason="Kayıt tamamlandı")

        eski_cins = ERKEK if ERKEK in [r.id for r in uye.roles] else KIZ if KIZ in [r.id for r in uye.roles] else None
        if eski_cins and eski_cins != rol_id:
            await uye.remove_roles(ctx.guild.get_role(eski_cins), reason="Cinsiyet güncellendi")
        if rol_id not in [r.id for r in uye.roles]:
            await uye.add_roles(cinsiyet_rol, reason="Cinsiyet seçildi")

        yeni_isim = f"{isim} | {yas}"
        if len(yeni_isim) > 32:
            yeni_isim = yeni_isim[:32]

        if kayitsiz_var:
            await uye.edit(nick=yeni_isim, reason="Kayıtsız → Kayıtlı: İsim güncellendi")
        elif not kayitsiz_kontrol:
            await uye.edit(nick=yeni_isim, reason="İsim güncellendi")

        baslik = "Kayıt Tamamlandı!" if kayitsiz_var else "Güncelleme Tamamlandı!"
        aciklama = f"{uye.mention} **{cinsiyet.upper()}** olarak {'kayıt edildi' if kayitsiz_var else 'güncellendi'}."

        embed = discord.Embed(
            title=baslik,
            description=aciklama,
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="İsim", value=yeni_isim, inline=True)
        embed.add_field(name="Yaş", value=yas, inline=True)
        embed.add_field(name="Cinsiyet", value=cinsiyet.title(), inline=True)
        embed.add_field(name="Üye Rolü", value=f"<@&{NOVA_UYE}>", inline=True)
        embed.set_footer(text="NOVA Ailesi")
        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send("Botun yetkisi yok! Rol hiyerarşisi kontrol et.")
    except Exception as e:
        await ctx.send("Hata oluştu.")
        print(f"[HATA] {e}")

# ========================================
# 7) Hata Yönetimi
# ========================================
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingRequiredArgument):
        cmd = ctx.command.name
        if cmd == "ksil":
            await ctx.send("Kullanım: `.ksil ÜYE_ID`")
        elif cmd == "sil":
            await ctx.send("Kullanım: `.sil <sayı>` veya `.sil clear`")
        else:
            await ctx.send(f"Kullanım: `.{cmd} @üye İsim Yaş ERKEK`")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Üye bulunamadı!")
    elif isinstance(error, commands.BadArgument):
        if ctx.command.name == "ksil":
            await ctx.send("Geçerli bir **ÜYE ID** girin!")
        else:
            await ctx.send("Yaş sayı olmalı!")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Bu komutu kullanma yetkin yok!")
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        print(f"[HATA] {error}")

# ========================================
# 8) Bot Hazır
# ========================================
@bot.event
async def on_ready():
    print(f"\nKayıt Botu aktif: {bot.user}")
    print(f"Sunucu sayısı: {len(bot.guilds)}")
    if KAYIT_KANALI != 0:
        print(f"Kayıt komutları sadece <#{KAYIT_KANALI}> kanalında çalışır.")
    print(f"KAYITSIZ ROL ID: {KAYITSIZ}")
    print("-" * 50)

# ========================================
# 9) Başlat
# ========================================
if __name__ == "__main__":
    bot.run(TOKEN)