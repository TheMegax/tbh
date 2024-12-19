import os.path
import pathlib
from typing import Type
from string import Template

import discord

from discord import Bot, Option, Embed, Color, IntegrationType, GroupChannel, RawReactionActionEvent
from discord.abc import User
from discord.ext.bridge import Context
from discord.ext.commands import dm_only, PrivateMessageOnly
from dotenv import load_dotenv

from html2image import Html2Image

import dbconnection
import html
from PIL import Image

import utils

load_dotenv()
TOKEN: str = os.getenv('DISCORD_TOKEN')
BROWSER: str = os.getenv('BROWSER', 'chrome')
BROWSER_LOCATION: str = os.getenv('BROWSER_LOCATION')

hti = Html2Image(disable_logging=True, browser=BROWSER, browser_executable=BROWSER_LOCATION)

# TODO(s)
#  Markdown for text
#  Customizable title gradient colors
#  Link website? So you don't need to use the discord app

# Initialize bot object
bot: Bot = discord.Bot()
send_group = bot.create_group(name="send", description=utils.localize("command.send.description"))
asks_group = bot.create_group(name="asks", description=utils.localize("command.asks.description"))
tbh_group = bot.create_group(name="tbh", description=utils.localize("command.tbh.description"))
send_group.integration_types = {IntegrationType.user_install}
asks_group.integration_types = {IntegrationType.user_install}
tbh_group.integration_types = {IntegrationType.user_install}


@asks_group.command(description=utils.localize("command.asks.enable.description"))
async def enable(ctx: Context) -> None:
    user = await dbconnection.get_or_create_user(ctx.user.id)
    await dbconnection.update_db_column("users", user.user_id, "user_id", "are_asks_open", 1)

    await ctx.send_response(ephemeral=True, embed=Embed(title=utils.localize("embed.asks.enable.title"),
                                                        description=utils.localize("embed.asks.enable.description")))


@asks_group.command(description=utils.localize("command.asks.disable.description"))
async def disable(ctx: Context) -> None:
    user = await dbconnection.get_or_create_user(ctx.user.id)
    await dbconnection.update_db_column("users", user.user_id, "user_id", "are_asks_open", 0)

    await ctx.send_response(ephemeral=True, embed=Embed(title=utils.localize("embed.asks.disable.title"),
                                                        description=utils.localize("embed.asks.disable.description")))


@asks_group.command(description=utils.localize("command.asks.clear.description"))
@dm_only()
async def clear(ctx: Context) -> None:
    await ctx.defer(ephemeral=True)
    db_user = await dbconnection.get_or_create_user(ctx.user.id)
    user = await bot.get_or_fetch_user(db_user.user_id)

    await user.create_dm()

    if user.dm_channel:
        if ctx.channel_id != user.dm_channel.id:
            raise PrivateMessageOnly
        async for msg in user.dm_channel.history():
            if msg.author.id != bot.user.id:
                continue
            await dbconnection.remove_ask(msg.id)
            await msg.delete()
    await ctx.send_followup(embed=Embed(title=utils.localize("success.title"),
                                        description=utils.localize("success.clear"), color=Color.green()))


@bot.command(description=utils.localize("command.link.description"),
             integration_types={IntegrationType.user_install})
async def link(ctx: Context,
               title: Option(str, input_type=Type[str],
                             description=utils.localize("command.link.title"),
                             default=utils.localize("template.default_ask"),
                             max_length=50
                             )
               ) -> None:
    await ctx.defer()
    user = await dbconnection.get_or_create_user(ctx.user.id)
    await dbconnection.update_db_column("users", user.user_id, "user_id", "are_asks_open", 1)
    await dbconnection.update_db_column("users", user.user_id, "user_id", "ask_title", title)
    utils.formatlog("Generating link {0}...".format(str(ctx.interaction.id)))
    img_name = generate_link_image(ask_title=title, img_id=ctx.interaction.id)
    embed = Embed(title=utils.localize("embed.link.title").format(ctx.user.display_name),
                  description=utils.localize("embed.link.description").format(utils.localize("template.app_link")))
    embed.set_image(url="attachment://" + img_name)

    await ctx.send_followup(file=discord.File(img_name), embed=embed)
    path = pathlib.Path(img_name)
    path.unlink(True)
    utils.formatlog("Link {0} sent!".format(str(ctx.interaction.id)))


@send_group.command(description=utils.localize("command.send.message.description"))
async def message(ctx: Context,
                  to: Option(User, input_type=Type[User],
                             description=utils.localize("command.send.message.to")
                             ),
                  msg: Option(str, input_type=Type[str],
                              description=utils.localize("command.send.message.msg"),
                              max_length=200
                              )
                  ) -> None:
    await ctx.defer(ephemeral=True)
    to: User = to

    await dbconnection.get_or_create_user(ctx.user.id)
    db_target = await dbconnection.get_or_create_user(to.id)

    target_usr = await bot.get_or_fetch_user(to.id)
    if target_usr is not None:
        if not db_target.are_asks_open:
            await ctx.send_followup(
                embed=Embed(title=utils.localize("error.title"), color=Color.red(),
                            description=utils.localize("error.asks_closed").format(target_usr.display_name)))
            return
        utils.formatlog("Sending ask {0}...".format(str(ctx.interaction.id)))
        img_name = generate_ask_image(ask_title=db_target.ask_title,
                                      ask_msg=msg, img_id=ctx.interaction.id)
        sent_msg = await target_usr.send(file=discord.File(img_name))
        await sent_msg.add_reaction("❌")
        await sent_msg.add_reaction("❔")

        if ctx.guild_id:
            origin = dbconnection.origins[1]
        elif isinstance(ctx.channel, GroupChannel):
            origin = dbconnection.origins[2]
        else:
            origin = dbconnection.origins[3]

        await dbconnection.get_or_create_ask(sent_msg.id, origin)
        await ctx.send_followup(
            delete_after=5,
            embed=Embed(title=utils.localize("success.title"), color=Color.green(),
                        description=utils.localize("success.sent").format(target_usr.display_name)))
        path = pathlib.Path(img_name)
        path.unlink(True)
        utils.formatlog("Ask {0} sent!".format(str(ctx.interaction.id)))
        return

    await ctx.send_followup(
        embed=Embed(title=utils.localize("error.title"),
                    color=Color.red(), description=utils.localize("error.unknown")))
    return


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    if error.args[0].__contains__('(error code: 50007)'):
        await ctx.respond(ephemeral=True,
                          embed=Embed(title=utils.localize("error.title"),
                                      color=Color.red(), description=utils.localize("error.no_app")))
    if isinstance(error, PrivateMessageOnly):
        await ctx.respond(ephemeral=True,
                          embed=Embed(title=utils.localize("error.title"),
                                      color=Color.red(), description=utils.localize("error.private_message_only"))
                          )
    else:
        utils.formatlog(f"{error.__class__.__name__}: {error.__str__()}")
        await ctx.respond(
            embed=Embed(title=utils.localize("error.title"),
                        color=Color.red(), description=utils.localize("error.unknown")))
    path = pathlib.Path("{0}.png".format(ctx.interaction.id))
    path.unlink(True)


@bot.event
async def on_ready() -> None:
    utils.formatlog(f'{bot.user} has connected to Discord!')
    await dbconnection.initialize_database()


async def handle_reactions(payload: RawReactionActionEvent) -> None:
    if payload.user_id == bot.user.id:
        return
    ask = await dbconnection.get_ask(payload.message_id)
    if ask:
        channel = await bot.fetch_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        if payload.emoji.name == "❌":
            await msg.delete()
            await dbconnection.remove_ask(ask.ask_id)
        elif payload.emoji.name == "❔":
            embed = Embed(title=utils.localize("embed.see_origin.title"),
                          description=utils.localize(f"embed.see_origin.{ask.origin}.description"))
            await msg.reply(embed=embed, delete_after=10)


@bot.event
async def on_raw_reaction_add(payload: RawReactionActionEvent) -> None:
    await handle_reactions(payload)


def generate_link_image(ask_title: str, img_id: int) -> str:
    ask_title = html.escape(ask_title)
    with open("html/link.html", "r") as file:
        data = file.read()

        html_temp = Template(data)
        html_filled = html_temp.substitute(ask_title=ask_title)
        output_name = "{0}.png".format(str(img_id))
        hti.screenshot(html_str=html_filled, save_as=output_name)
        crop_image(output_name)
    return output_name


def generate_ask_image(ask_title: str, ask_msg: str, img_id: int) -> str:
    ask_title = html.escape(ask_title)
    ask_msg = html.escape(ask_msg)
    with open("html/answer.html", "r") as file:
        data = file.read()

        html_temp = Template(data)
        html_filled = html_temp.substitute(ask_title=ask_title, ask_msg=ask_msg)
        output_name = "{0}.png".format(str(img_id))
        hti.screenshot(html_str=html_filled, save_as=output_name)
        crop_image(output_name)
    return output_name


def crop_image(img_dir):
    im = Image.open(img_dir)

    width, height = im.size
    p1_x = 300
    p1_y = 50
    p2_x = width - 300
    p2_y = height - 50

    im.crop((p1_x, p1_y, p2_x, p2_y)).save(img_dir)


bot.run(TOKEN)
