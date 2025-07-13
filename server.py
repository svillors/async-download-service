import asyncio
import os
import logging

import aiofiles
from aiohttp import web


logging.basicConfig(level=logging.INFO)


async def archive(request):
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'

    archive_hash = request.match_info.get('archive_hash')
    files_path = os.path.join('.', 'photos', archive_hash)
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
        while True:
            chunk = await proc.stdout.read(250)
            if not chunk:
                logging.info('')
                break
            logging.info('Sending archive chunk ...')
            await response.write(chunk)
    except asyncio.CancelledError:
        logging.info('Download was interrupted')
    except BaseException as e:
        logging.error(f'error while downloading archive: {type(e).__name__}')
    finally:
        proc.kill()
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
