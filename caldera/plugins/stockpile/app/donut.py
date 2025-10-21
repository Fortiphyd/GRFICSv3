import donut
import os
import base64
import shlex


async def donut_handler(services, args):
    """Handle donut special payloads

    Creates .donut files from the .donut.exe files created by the
    builder plugin

    :param services: Caldera services
    :type services: dict
    :param args: HTTP request arguments
    :type args: multidict
    :return: Payload, display name
    :rtype: string, string
    """
    donut_file = args.get('file')
    exe_path = await _get_exe_path(services, donut_file)
    if exe_path:
        donut_dir, _ = os.path.split(exe_path)
        donut_path = os.path.join(donut_dir, donut_file)
        parameters = await _get_parameters(services.get('data_svc'), donut_file, args.get('X-Link-Id'))
        shellcode = donut.create(file=exe_path, params=parameters)
        _write_shellcode_to_file(shellcode, donut_path)
    else:
        print('[!] No executable found for donut payload: {}'.format(donut_file))

    return donut_file, donut_file


""" PRIVATE """


async def _get_exe_path(services, donut_file):
    """Get executable path for payload

    Example:
        donut_file = 'Rubeus.donut'
        Search for:
            1. 'Rubeus.donut.exe'
            2. 'Rubeus.exe'

    :param services: Caldera services
    :type services: dict
    :param donut_file: Donut filename
    :type donut_file: string
    :return: Full path to executable
    :rtype: string
    """
    base_name = os.path.splitext(donut_file)[0]
    exe_files = [
        '{}.exe'.format(donut_file),
        '{}.exe'.format(base_name)
    ]
    for exe_file in exe_files:
        _, exe_path = await services.get('file_svc').find_file_path(exe_file, location='payloads')
        if exe_path:
            break
    return exe_path


def _write_shellcode_to_file(shellcode, file_path):
    """Write shellcode to file path

    :param shellcode: Shellcode byte string
    :type shellcode: bytes
    :param file_path: File path to write to
    :type file_path: string
    """
    try:
        with open(file_path, 'wb') as f:
            f.write(shellcode)
    except Exception as ex:
        print(ex)


async def _get_parameters(data_svc, file_name, link_id=None):
    """Generate command line parameters link or best guess

    Links are matched based on the earliest started matching ability if
    `link_id` is not defined

    This will only work with the plain-text obfuscator.

    Parameters are everything after the first instance of the payload
    (donut file name) in the ability command.

    Note: In donut 0.9.2, the parameters are based using a comma or
    semi-colon split. Any parameters containing a comma may break this
    parsing.

    :param data_svc: Data service to collect operations
    :type data_svc: DataService
    :param file_name: Donut filename
    :type file_name: str
    :param link_id: Link ID for command
    :type link_id: str
    :return: Donut parameters
    :rtype: string
    """
    parameters = []
    operations = await data_svc.locate('operations', match=dict(state='running'))
    if link_id:
        potential_links = [link for operation in operations for link in operation.chain if link.id == link_id]
    else:
        potential_links = [link for operation in operations for link in operation.chain
                           if not link.finish and link.executor.name.startswith('donut')
                           and file_name in link.executor.payloads]
    if potential_links:
        link = sorted(potential_links, key=lambda l: l.decide)[0]
        operation = [operation for operation in operations if operation.has_link(link.id)][0]
        if operation.obfuscator == 'plain-text':
            decoded_command = base64.b64decode(link.command).decode('utf-8')
            if file_name in decoded_command:
                parameters = shlex.split(''.join(decoded_command.split(file_name)[1:]))
            else:
                print('[!] Donut file name missing from command in ability "{}". Prepend "{}"'.format(link.ability.name,
                                                                                                      file_name))
                print('[!] {} may need to be deleted from the remote machine.'.format(file_name))
                parameters = shlex.split(decoded_command)
    return ','.join(parameters)
