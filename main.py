import json
import os.path
from typing import Type
from string import Template

import discord

from discord import Bot, Option, Embed, Color, IntegrationType, ComponentType, EmbedMedia
from discord.abc import User
from discord.ext.bridge import Context
from discord.ui import Item
from dotenv import load_dotenv

from html2image import Html2Image
from PIL import Image

hti = Html2Image()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configure localization
with open("localization/en-US.json") as f:
    localization: dict = json.load(f)


def localize(key: str):
    if key not in localization:
        return key
    return localization[key]


class SelectUserView(discord.ui.View):
    @discord.ui.select(
        placeholder="Send to..? (Must be in members list)",
        select_type=ComponentType.user_select
    )
    async def select_callback(self, select, interaction: discord.Interaction):
        usr: User = select.values[0]
        await interaction.response.send_modal(
            SendMsgModal(usr=usr, custom_id="msg_modal", title="Sending anonymous message to " + usr.name))
        await interaction.delete_original_response()


class DeleteAskView(discord.ui.View):
    # noinspection PyUnusedLocal
    @discord.ui.button(label="Delete Ask", style=discord.ButtonStyle.danger)
    async def button_callback(self, button, interaction: discord.Interaction):
        await interaction.message.delete()


class SendAgainView(discord.ui.View):
    user: User

    def __init__(self, usr=None, *items: Item) -> None:
        self.user = usr
        super().__init__(*items)

    # noinspection PyUnusedLocal
    @discord.ui.button(label="Send another", style=discord.ButtonStyle.primary)
    async def button_callback(self, button, interaction):
        await interaction.response.send_modal(SendMsgModal(usr=self.user, custom_id="msg_modal",
                                                           title="Sending anonymous message to " + self.user.name))
        await interaction.delete_original_response()


class SendMsgModal(discord.ui.Modal):
    user: User

    def __init__(self, usr=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = usr
        self.add_item(discord.ui.InputText(custom_id="msg_input", label="Message", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        usr = await bot.get_or_fetch_user(self.user.id)
        if usr is not None:
            msg = self.children[0].value
            await usr.send(content=msg, view=DeleteAskView())
            embed = discord.Embed(title=localize("success.title"), color=Color.green(),
                                  description=localize("success.sent").format(self.user.display_name))
            await interaction.response.send_message(ephemeral=True, embeds=[embed], view=SendAgainView(usr=self.user))
            return

        await interaction.response.send_message(
            ephemeral=True, embed=Embed(title=localize("error.title"),
                                        color=Color.red(),
                                        description=localize("error.unknown")))


# Initialize bot object
bot: Bot = discord.Bot()
send_group = bot.create_group(name="send", description=localize("command.send.description"))
send_group.integration_types = {IntegrationType.user_install}


@bot.command(description=localize("command.link.description"),
             integration_types={IntegrationType.user_install})
async def link(ctx: Context,
               title: Option(str, input_type=Type[str],
                             description=localize("command.link.title"),
                             default="Send me anonymous messages"
                             )
               ) -> None:
    await ctx.defer()
    generate_link_image(title)
    embed = Embed(title=localize("embed.link.title").format(ctx.user.display_name))
    embed.set_image(url="attachment://output.png")

    await ctx.send_followup(file=discord.File("output.png"), embed=embed)


@send_group.command(description=localize("command.send.message.description"))
async def message(ctx: Context,
                  to: Option(User, input_type=Type[User],
                             description=localize("command.send.message.to")
                             ),
                  msg: Option(str, input_type=Type[str],
                              description=localize("command.send.message.msg")
                              )
                  ) -> None:
    await ctx.defer(ephemeral=True)

    to: User = to
    usr = await bot.get_or_fetch_user(to.id)
    if usr is not None:
        generate_ask_image("Ask me anything!", ask_msg=msg)
        await usr.send(file=discord.File("output.png"), view=DeleteAskView())
        await ctx.send_followup(
            embed=Embed(title=localize("success.title"), color=Color.green(),
                        description=localize("success.sent").format(usr.name)))

        return

    await ctx.send_followup(
        embed=Embed(title=localize("error.title"), color=Color.red(), description=localize("error.unknown")))
    return


# @send_group.command(description="dont mind me...")
async def message2(ctx: Context) -> None:
    await ctx.send_response(ephemeral=True, view=SelectUserView())


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    if error.args[0].__contains__('(error code: 50007)'):
        await ctx.respond(
            embed=Embed(title=localize("error.title"), color=Color.red(), description=localize("error.no_app")))
    else:
        print(error.args)
        print(error.__class__.__name__, error)
        await ctx.respond(
            embed=Embed(title=localize("error.title"), color=Color.red(), description=localize("error.unknown")))


@bot.event
async def on_ready() -> None:
    print(f'{bot.user} has connected to Discord!')


def generate_link_image(ask_title: str) -> None:
    with open("html/link.html", "r") as file:
        data = file.read()

        html_temp = Template(data)
        html_filled = html_temp.substitute(ask_title=ask_title)
        hti.screenshot(html_str=html_filled, save_as="output.png")
        crop_image()


def generate_ask_image(ask_title: str, ask_msg: str) -> None:
    with open("html/answer.html", "r") as file:
        data = file.read()

        html_temp = Template(data)
        html_filled = html_temp.substitute(ask_title=ask_title, ask_msg=ask_msg)
        hti.screenshot(html_str=html_filled, save_as="output.png")
        crop_image()


def crop_image():
    im = Image.open("output.png")

    width, height = im.size
    p1_x = 300
    p1_y = 50
    p2_x = width - 300
    p2_y = height - 50

    im.crop((p1_x, p1_y, p2_x, p2_y)).save("output.png")


bot.run(TOKEN)
