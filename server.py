import asyncio
import os
import logging
import argparse

import aiofiles
from aiohttp import web


async def archive(request):
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'

    archive_hash = request.match_info['archive_hash']
    folder_path = request.app.get('photos_path')
    files_path = os.path.join(folder_path, archive_hash)

    delay = request.app.get('delay')

    if not os.path.exists(files_path):
        logging.error('Error 404: link to non-existent folder')
        raise web.HTTPNotFound(
            text='Error 404\nАрхив не существует или был удален')

    await response.prepare(request)

    files = os.listdir(files_path)
    proc = await asyncio.subprocess.create_subprocess_exec(
        'zip', '-r', '-', *files,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=files_path
    )
    try:
        chunk = True
        while chunk:
            chunk = await proc.stdout.read(250)
            logging.info('Sending archive chunk ...')
            await response.write(chunk)
            if delay:
                await asyncio.sleep(delay)
        else:
            logging.info('archive downloaded')
    except asyncio.CancelledError:
        logging.info('Download was interrupted')
        raise
    except BaseException as e:
        logging.error(f'error while downloading archive: {type(e).__name__}')
    finally:
        proc.kill()
        await proc.communicate()
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    parser = argparse.ArgumentParser(description='Archive download server')
    parser.add_argument(
        '-p', '--photos-path',
        default=os.path.join('.', 'photos'),
        help='path to photo archives'
    )
    parser.add_argument(
        '-d', '--delay',
        default=None,
        type=float,
        help='loading delay between chunks'
    )
    parser.add_argument(
        '-nl', '--no-logging',
        action='store_false',
        dest='logging_enabled',
        help='run without logging'
    )
    args = parser.parse_args()
    app['photos_path'] = args.photos_path
    app['delay'] = args.delay
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    if args.logging_enabled:
        logging.basicConfig(level=logging.INFO)
    logging.info('server startup...')
    web.run_app(app)
