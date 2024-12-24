import asyncio
import os.path
import pathlib
import random
from typing import Type

import discord

from discord import Bot, Option, Embed, Color, IntegrationType, GroupChannel, RawReactionActionEvent
from discord.abc import User
from discord.ext.bridge import Context
from discord.ext.commands import dm_only, PrivateMessageOnly
from dotenv import load_dotenv

import dbconnection
import utils

load_dotenv()
TOKEN: str = os.getenv('DISCORD_TOKEN')

# TODO(s)
#  Markdown for text
#  Customizable title gradient colors
#  Link website? So you don't need to use the discord app

# Initialize bot object
bot: Bot = discord.Bot()

send_group = bot.create_group(name="send", description=utils.localize("command.send.description"))
inbox_group = bot.create_group(name="inbox", description=utils.localize("command.inbox.description"))
tbh_group = bot.create_group(name="tbh", description=utils.localize("command.tbh.description"))
send_group.integration_types = {IntegrationType.user_install}
inbox_group.integration_types = {IntegrationType.user_install}
tbh_group.integration_types = {IntegrationType.user_install}


@tbh_group.command(description=utils.localize("command.tbh.help"))
async def help(ctx: Context) -> None:
    await ctx.send_response(ephemeral=True, embed=Embed(title=utils.localize("embed.tbh.help.title"),
                                                        description=utils.localize("embed.tbh.help.description")))


@inbox_group.command(description=utils.localize("command.inbox.enable.description"))
async def enable(ctx: Context) -> None:
    db_user = dbconnection.get_or_create_db_user(ctx.user.id, ctx.user.name)
    db_user.is_inbox_open = True
    dbconnection.update_db_user(db_user)

    await ctx.send_response(ephemeral=True, embed=Embed(title=utils.localize("embed.inbox.enable.title"),
                                                        description=utils.localize("embed.inbox.enable.description")))


@inbox_group.command(description=utils.localize("command.inbox.disable.description"))
async def disable(ctx: Context) -> None:
    db_user = dbconnection.get_or_create_db_user(ctx.user.id, ctx.user.name)
    db_user.is_inbox_open = False
    dbconnection.update_db_user(db_user)

    await ctx.send_response(ephemeral=True, embed=Embed(title=utils.localize("embed.inbox.disable.title"),
                                                        description=utils.localize("embed.inbox.disable.description")))


@inbox_group.command(description=utils.localize("command.inbox.clear.description"))
@dm_only()
async def clear(ctx: Context) -> None:
    await ctx.defer(ephemeral=True)
    db_user = dbconnection.get_or_create_db_user(ctx.user.id, ctx.user.name)
    user = await bot.get_or_fetch_user(db_user.user_id)

    await user.create_dm()

    if user.dm_channel:
        if ctx.channel_id != user.dm_channel.id:
            raise PrivateMessageOnly
        async for msg in user.dm_channel.history():
            if msg.author.id != bot.user.id:
                continue
            dbconnection.delete_db_message(msg.id)
            await msg.delete()
    await ctx.send_followup(embed=Embed(title=utils.localize("success.title"),
                                        description=utils.localize("success.clear"), color=Color.green()))


@bot.command(description=utils.localize("command.link.description"),
             integration_types={IntegrationType.user_install})
async def link(ctx: Context,
               title: Option(str, input_type=Type[str],
                             description=utils.localize("command.link.title"),
                             required=False,
                             max_length=100
                             )
               ) -> None:
    await ctx.defer()
    db_user = dbconnection.get_or_create_db_user(ctx.user.id, ctx.user.name)
    db_user.is_inbox_open = True
    if title is None:
        title = db_user.inbox_title
    else:
        db_user.inbox_title = title
    dbconnection.update_db_user(db_user)
    utils.formatlog("Generating link {0}...".format(str(ctx.interaction.id)))
    img_name = utils.generate_link_image(inbox_title=title, img_id=ctx.interaction.id)
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
                              max_length=300
                              )
                  ) -> None:
    await ctx.defer(ephemeral=True)
    to: User = to

    dbconnection.get_or_create_db_user(ctx.user.id, ctx.user.name)
    db_target = dbconnection.get_or_create_db_user(to.id, to.name)

    target_usr = await bot.get_or_fetch_user(to.id)
    if target_usr is not None:
        if not db_target.is_inbox_open:
            await ctx.send_followup(
                embed=Embed(title=utils.localize("error.title"), color=Color.red(),
                            description=utils.localize("error.inbox_closed").format(target_usr.display_name)))
            return
        utils.formatlog("Sending message {0}...".format(str(ctx.interaction.id)))
        img_name = utils.generate_message_image(inbox_title=db_target.inbox_title,
                                                msg=msg, img_id=ctx.interaction.id)
        sent_msg = await target_usr.send(file=discord.File(img_name))
        await sent_msg.add_reaction("❌")
        await sent_msg.add_reaction("❔")

        if ctx.guild_id:
            origin = dbconnection.origins[1]
        elif isinstance(ctx.channel, GroupChannel):
            origin = dbconnection.origins[2]
        else:
            origin = dbconnection.origins[3]

        dbconnection.create_db_message(sent_msg.id, origin)
        await ctx.send_followup(
            delete_after=5,
            embed=Embed(title=utils.localize("success.title"), color=Color.green(),
                        description=utils.localize("success.sent").format(target_usr.display_name)))
        path = pathlib.Path(img_name)
        path.unlink(True)
        utils.formatlog("Message {0} sent!".format(str(ctx.interaction.id)))
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
    print("BOT STARTED")
    utils.formatlog(f'{bot.user} has connected to Discord!')
    await dbconnection.initialize_database()


@bot.event
async def on_connect() -> None:
    bot.loop.create_task(queue_listener())


@bot.event
async def on_raw_reaction_add(payload: RawReactionActionEvent) -> None:
    await handle_reactions(payload)


async def handle_reactions(payload: RawReactionActionEvent) -> None:
    if payload.user_id == bot.user.id:
        return
    db_message = dbconnection.get_db_message(payload.message_id)
    if db_message:
        channel = await bot.fetch_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        if payload.emoji.name == "❌":
            await msg.delete()
            dbconnection.delete_db_message(db_message.message_id)
        elif payload.emoji.name == "❔":
            embed = Embed(title=utils.localize("embed.see_origin.title"),
                          description=utils.localize(f"embed.see_origin.{db_message.origin}.description"))
            await msg.reply(embed=embed, delete_after=10)


message_queue = asyncio.Queue()


async def queue_listener():
    while True:
        db_user_id, msg = await message_queue.get()
        to_user = dbconnection.get_or_create_db_user(db_user_id)
        await send_message_from_web(to_user, msg)
        message_queue.task_done()


async def send_message_from_web(to_user, msg):
    target_usr = await bot.get_or_fetch_user(to_user.user_id)
    if target_usr is None or not to_user.is_inbox_open:
        utils.formatlog("Nope")
        return
    rand_id = random.randint(1000000, 9999999)
    utils.formatlog("Sending message from web...")
    img_name = utils.generate_message_image(inbox_title=to_user.inbox_title,
                                            msg=msg, img_id=rand_id)
    sent_msg = await target_usr.send(file=discord.File(img_name))
    await sent_msg.add_reaction("❌")
    await sent_msg.add_reaction("❔")

    origin = dbconnection.origins[4]
    dbconnection.create_db_message(sent_msg.id, origin)

    path = pathlib.Path(img_name)
    path.unlink(True)
    utils.formatlog("Message {0} sent!".format(str(sent_msg.id)))


async def start_bot(token):
    await bot.start(token)
