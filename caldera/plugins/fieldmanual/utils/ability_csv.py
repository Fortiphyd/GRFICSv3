import argparse
import csv
import pathlib
import sys

import yaml


OUTPUT_COLUMNS = [
    'id',
    'plugin',
    'name',
    'description',
    'tactic',
    'technique_id',
    'technique_name',
]


def _parse_plugin_name(ability_file_path):
    ability_file_path = str(ability_file_path)
    plugin_prefix = 'plugins/'
    plugin_start_idx = ability_file_path.find(plugin_prefix) + len(plugin_prefix)
    plugin_name = ability_file_path[
                  plugin_start_idx:  plugin_start_idx + ability_file_path[plugin_start_idx:].find('/')
                  ]
    return plugin_name


def _transform_ability(ability_dict, plugin_name=''):
    return {
        'plugin': plugin_name,
        'id': ability_dict['id'],
        'name': ability_dict.get('name', ''),
        'description': ability_dict.get('description', ''),
        'tactic': ability_dict.get('tactic', ''),
        'technique_id': ability_dict.get('technique', {}).get('attack_id', ''),
        'technique_name': ability_dict.get('technique', {}).get('name', '')
    }


def generate_ability_csv(caldera_dir, dest_file='abilities.csv'):
    dest_path = pathlib.Path(dest_file)
    caldera_path = pathlib.Path(caldera_dir).resolve()
    caldera_data_backup_path = caldera_path / 'data' / 'backup'

    print(f'Searching for and processing ability files in {caldera_path.absolute()}')

    ability_count = 0
    with dest_path.open('w', newline='') as fle:
        writer = csv.DictWriter(fle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for ability_file in caldera_path.glob('**/abilities/*/*.yml'):
            # Skip the backup directory in case someone opened up backup tar.gz file in there.
            if caldera_data_backup_path in ability_file.parents:
                continue

            raw_ability = ability_file.read_text()

            if not raw_ability:
                continue

            ability = yaml.safe_load(ability_file.read_text())[0]
            output_ability = _transform_ability(ability, plugin_name=_parse_plugin_name(ability_file))
            writer.writerow(output_ability)
            ability_count += 1

    print(f'Processed {ability_count} abilities and wrote results to {dest_path.absolute()}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--caldera-dir', dest='caldera_dir', default='',
                        help='The path to the root caldera directory, the script will recursively search here'
                             'for ability files.')
    parser.add_argument('--dest-file', dest='dest_file', default='abilities.csv',
                        help='The output path. A csv file will be written to this path.')

    args = parser.parse_args()

    cal_dir = args.caldera_dir
    if not cal_dir:
        for parent in pathlib.Path().cwd().parents:
            if parent.name == 'caldera':
                caldera_dir = parent
                break

    if not cal_dir:
        print('Could not locate caldera dir.  Specify it with the "--caldera-dir" option')
        sys.exit(-1)

    generate_ability_csv(cal_dir)
