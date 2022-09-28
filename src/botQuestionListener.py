import json
import discord
import os
from datetime import datetime, timedelta
import pickle
import logging

from botBasics import setup_bot
bot, token = setup_bot()

from utils.helper import get_msginfo_filename
from utils.messageProcessing import embed, preprocess_messages, msgs_to_dict, get_matches

THUMBSUP = '\U0001f44d'
THUMBSDOWN = '\U0001f44e'
BOT_ID = '><'
v = 2

active_guilds = {}

@bot.event
async def on_ready():
    print('Bot is running')


@bot.event
async def on_message(msg):
    guild = msg.channel.guild
    # only process messages in active guilds
    if str(guild.id) not in active_guilds:
        return
    # if message is from our bot, add upvote and downvote reaction for user feedback
    if str(msg.author.id) in [BOT_ID]:
        try:
            await msg.add_reaction(THUMBSUP)
            await msg.add_reaction(THUMBSDOWN)
        except discord.errors.Forbidden:
            pass
        return
    # ignore server-generated messages (e.g. new user joined)
    if len(msg.content) == 0 and len(msg.attachments) == 0:
        return

    id = f'{guild.id}'

    # get recent msgs to combine subsequent user messages and check if author had been active recently (influences question classification)
    msgs = await msg.channel.history(limit=None, oldest_first=True,
                                     after=datetime.today() - timedelta(days=1)).flatten()
    msgs = msgs_to_dict(msgs)
    msgs = preprocess_messages(msgs, should_remove_lost_replies=False, classify_questions='last')
    if len(msgs) == 0:
        # probably a channel where only msgs are that users joined the server
        return
    m = msgs[-1]
    is_question = m['is_question']
    if not is_question:
        return
    with open(get_msginfo_filename(id, v=v), "rb") as f:
        msg_info = pickle.load(f)
    # only find matches for questions from different authors
    allowed_msg_ids = [mid for mid, repl_m in msg_info.items() if
                       'answer' in repl_m and repl_m['author']['id'] != m['author']['id']]
    result = get_matches(id, m['content'], n=1, allowed_msg_ids=allowed_msg_ids, v=v)
    channel_info = {'channel': {'id': msg.channel.id, 'name': msg.channel.name},
                    'guild': {'id': msg.channel.guild.id, 'name': msg.channel.guild.name}}
    sim_thresh = 0.52
    if result is not None:
        match_ids, match_sims = result
        print(match_sims[0])
        repl_m = msg_info[match_ids[0]]
        answer = f'<@{msg.author.id}> This question is similar, check out its answers to see if it helps.'
        if match_sims[0] >= sim_thresh:
            repl_m_content = repl_m['content'].replace('\n', ' ').replace('  ', ' ')
            if len(repl_m_content) > 200:
                repl_m_content = repl_m_content[:200]
                repl_m_content_new = repl_m_content[:-len(repl_m_content.split(' ')[-1])]
            link_msg_id = repl_m["id"]
            jump_url = f'https://discord.com/channels/{repl_m["server_id"]}/{repl_m["channel_id"]}/{link_msg_id}'
            embedVar = discord.Embed(description=f'**This question is similar, check out its answers to see if it helps:**\n[{repl_m_content}]({jump_url})', color=0x823FD7)
            try:
                bot_msg = await msg.reply(embed=embedVar)
            except discord.errors.Forbidden as e:
                pass


@bot.event
async def on_reaction_add(reaction, user):
    msg = reaction.message
    # 2nd is test bot
    if str(user.id) in [BOT_ID] or str(msg.author.id) not in [BOT_ID]:
        return
    msg_id = msg.id
    reactions = {r.emoji: r.count for r in msg.reactions}
    if reactions[THUMBSUP] < reactions[THUMBSDOWN]:
        await msg.delete()


bot.run(token)
