import discord
from discord.ext import commands
from tabulate import tabulate

from . import utils as vbu


_ = vbu.translation


class BotSettings(vbu.Cog):

    @vbu.group(name="command")
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @vbu.checks.is_config_set("database", "enabled")
    async def _command(self, ctx: vbu.Context) -> None:
        """
        Manage command settings.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @_command.command(name="disable")
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @vbu.checks.is_config_set("database", "enabled")
    async def _command_disable(self, ctx: vbu.Context, *, command: str) -> None:
        """
        Disable a command.
        """

        command = command.lower()
        if not ctx.bot.get_command(command):
            await ctx.send(f"The command `{command}` was not found.")
            return
        async with vbu.Database() as db:
            alr_in_db = await db(
                "SELECT * FROM command_settings WHERE guild_id = $1 AND command = $2",
                ctx.guild.id,
                command,
            )
            if alr_in_db:
                await ctx.send(f"The command `{command}` is already disabled.")
                return
            await db(
                "INSERT INTO command_settings (guild_id, command, enabled) VALUES ($1, $2, $3)",
                ctx.guild.id,
                command,
                int(False),
            )
            self.bot.default_guild_disabled_commands[ctx.guild.id][command] = False
        await ctx.send(f"The command `{command}` was disabled.")

    @_command.command(name="enable")
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @vbu.checks.is_config_set("database", "enabled")
    async def _command_enable(self, ctx: vbu.Context, *, command: str) -> None:
        """
        Enable a command.
        """

        command = command.lower()
        if not ctx.bot.get_command(command):
            await ctx.send(f"The command `{command}` was not found.")
            return
        async with vbu.Database() as db:
            alr_in_db = await db(
                "SELECT * FROM command_settings WHERE guild_id = $1 AND command = $2",
                ctx.guild.id,
                command,
            )
            if alr_in_db:
                await db(
                    "DELETE FROM command_settings WHERE guild_id = $1 AND command = $2",
                    ctx.guild.id,
                    command,
                )
                try:
                    del self.bot.default_guild_disabled_commands[ctx.guild.id][command]
                except KeyError:
                    pass
                await ctx.send(f"The command `{command}` was enabled.")
                return
            await ctx.send(f"The command `{command}` is already enabled.")

    @_command.command(name="list")
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @vbu.checks.is_config_set("database", "enabled")
    async def _command_list(self, ctx: vbu.Context) -> None:
        """
        List all disabled commands.
        """

        async with vbu.Database() as db:
            _commands = await db(
                "SELECT * FROM command_settings WHERE guild_id = $1", ctx.guild.id
            )
        if not _commands:
            await ctx.send("No commands found.")
            return
        _commands = [command["command"] for command in _commands]
        fmt = []
        for command in _commands:
            if c := ctx.bot.get_command(command):
                if not isinstance(c, commands.Group):
                    fmt.append((c.name, "True"))
                else:
                    for x in c.commands:
                        fmt.append((f"{c.name} " + x.name, "True"))
        await vbu.embeddify(
            ctx,
            "`" * 3
            + "ml\n"
            + tabulate(fmt, headers=["command", "disabled"], tablefmt="psql")
            + "\n"
            + "`" * 3,
        )

    @vbu.command(add_slash_command=False)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    @vbu.checks.is_config_set('database', 'enabled')
    async def prefix(self, ctx: vbu.Context, *, new_prefix: str = None):
        """
        Changes the prefix that the bot uses.
        """

        # See if the prefix was actually specified
        prefix_column = self.bot.config.get('guild_settings_prefix_column', 'prefix')
        if new_prefix is None:
            current_prefix = self.bot.guild_settings[ctx.guild.id][prefix_column] or self.bot.config['default_prefix']
            return await ctx.send(
                _(ctx, "bot_settings").gettext(f"The current prefix is `{current_prefix}`."),
                allowed_mentions=discord.AllowedMentions.none(),
            )

        # See if the user has permission
        try:
            await commands.has_guild_permissions(manage_guild=True).predicate(ctx)
        except Exception:
            return await ctx.send(_(ctx, "bot_settings").gettext("You do not have permission to change the command prefix."))

        # Validate prefix
        if len(new_prefix) > 30:
            return await ctx.send(_(ctx, "bot_settings").gettext("The maximum length a prefix can be is 30 characters."))

        # Store setting
        self.bot.guild_settings[ctx.guild.id][prefix_column] = new_prefix
        async with self.bot.database() as db:
            await db(
                """INSERT INTO guild_settings (guild_id, {prefix_column}) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET {prefix_column}=excluded.prefix""".format(prefix_column=prefix_column),
                ctx.guild.id, new_prefix
            )
        await ctx.send(
            _(ctx, "bot_settings").gettext(f"My prefix has been updated to `{new_prefix}`."),
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: vbu.Bot):
    x = BotSettings(bot)
    await bot.add_cog(x)
