from typing import Dict, Union
from zulip_bots.lib import BotHandler
import requests
import logging
from requests.exceptions import HTTPError, ConnectionError

from zulip_bots.custom_exceptions import ConfigValidationError

TENOR_SEARCH = "https://g.tenor.com/v1/random?contentfilter=high&media_filter=minimal"
TENOR_RANDOM = "https://g.tenor.com/v1/random?contentfilter=high&media_filter=minimal"
LMT = 1

class GifBotHandler:
    """
    This plugin posts a GIF response to keywords provided by the user. Images are
    provided by Tenor, through their API.
    """
    def usage(self) -> str:
        return '''
            This plugin will respond with gifs from Tenor.
            It will reply to @gifme with a gif of whatever your message contains.
            '''

    @staticmethod
    def validate_config(config_info: Dict[str, str]) -> None:
        search_term = "excited"
        try:
            url = TENOR_SEARCH
            payload = {'q': search_term, 'key': config_info['api-key'], 'limit': LMT}
            data = requests.get(url, payload)
        except ConnectionError as e:
            raise ConfigValidationError(str(e))
        except HTTPError as e:
            error_message = str(e)
            if data.status_code == 403:
                error_message += ('This is likely due to an invalid key. \n')
            raise ConfigValidationError(error_message)

    def initialize(self, bot_handler: BotHandler) -> None:
        self.config_info = bot_handler.get_config_info('gifme')

    def handle_message(self, message: Dict[str, str], bot_handler: BotHandler) -> None:
        bot_response = get_bot_response(
            message,
            bot_handler,
            self.config_info
        )
        bot_handler.send_reply(message, bot_response)

class TenorNoResultException(Exception):
    pass

def get_url_gif_tenor(keyword: str, api_key: str) -> Union[int, str]:
    # Return a URL for a Tenor GIF based on keywords given.
    # In case of error, e.g. failure to fetch a GIF URL, it will
    # return a number.
    print('keyword= ' + keyword)
    if len(keyword) > 0:
        url = TENOR_SEARCH
        payload = {'q': keyword, 'key': api_key, 'limit': LMT}
    else:
        url = TENOR_RANDOM
        payload = {'key': api_key}
    try:
        data = requests.get(url, params=payload)
        print(data.url) #Debug
    except requests.exceptions.ConnectionError:  # Usually triggered by bad connection.
        logging.exception('Bad connection')
        raise
    data.raise_for_status()

    try:
        gif_url = data.json()['results'][0]['media'][0]['tinygif']['url']
        print(gif_url) #Debug
    except (TypeError, KeyError):  # Usually triggered by no result in Tenor.
        raise TenorNoResultException()
    except (TypeError, IndexError):
        raise TenorNoResultException()
    return gif_url

# accept the content of msg split into array
def normalize_query(arr):
    query = '+'.join(arr[2:])
    print('query= ' + query) #Debug
    return query.lower()

def get_bot_response(message: Dict[str, str], bot_handler: BotHandler, config_info: Dict[str, str]) -> str:
    # Each exception has a specific reply should "gif_url" return a number.
    # The bot will post the appropriate message for the error.
    if message['sender_email'] !="gifme-bot@zulip-test.meyertool.com":
        keyword = message['content']
        #bot only sends msg back when messaged "gifme", "gif me", or "@gifme"
#        if((content[0] == "gifme")
#            or (content[0]=="gif" and content[1]=="me")
#           or (content[0]=="@**gifme**")):
#
#            keyword = normalize_query(content)
    try:
        gif_url = get_url_gif_tenor(keyword, config_info['api-key'])
    except requests.exceptions.ConnectionError:
        return ('Uh oh, sorry :slightly_frowning_face:, I '
                'cannot process your request right now. But, '
                'let\'s try again later! :grin:')
    except TenorNoResultException:
        return ('Sorry, I don\'t have a GIF for "%s"!'
                ':astonished:'
                 % (keyword,))
    return ('[Click to enlarge](%s)'
            % (gif_url,))

handler_class = GifBotHandler
