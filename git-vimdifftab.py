#!/usr/bin/python

import sys, subprocess, os, os.path, tempfile, shutil

def copy_if_tmp(file_dir, file_name):
    # files without that look like temp files need to be copied
    if not os.path.isabs(file_name): return file_name

    file_name_out = os.path.join(file_dir, os.path.basename(file_name))
    shutil.copy(file_name, file_name_out)
    return file_name_out

# if this is a child
manifest_file_name = os.getenv('GIT_VIMDIFFTAB')
if manifest_file_name != None:
    # TODO use lockfile

    file_dir = os.path.dirname(manifest_file_name)

    file_name1 = copy_if_tmp(file_dir, sys.argv[1])
    file_name2 = copy_if_tmp(file_dir, sys.argv[2])

    manifest_file = open(manifest_file_name, 'a')
    manifest_file.write(file_name1 + '\n' + file_name2 + '\n');

    sys.exit(0)

# create the dir and pass it to the children
temp_dir = tempfile.mkdtemp('', 'git-vimdifftab-' + str(os.getpid()) + '-')
manifest_file_fd, manifest_file_name = tempfile.mkstemp('.manifest', '',
        temp_dir, True)
os.putenv('GIT_VIMDIFFTAB', manifest_file_name)

script_name = sys.argv[0]
if script_name == '-c':
    raise Error('Script must be called dirctly, not run from interpreter')

git_diff_rc = subprocess.call(
    ['git', 'difftool', '--no-prompt',
            '--extcmd=' + script_name] + sys.argv[1:])
if git_diff_rc != os.EX_OK:
    raise Error('git difftool failed: ' + str(git_diff_rc))

vim_file_fd, vim_file_name = tempfile.mkstemp('.vim', '', temp_dir, True)
vim_file = os.fdopen(vim_file_fd, 'a')

# TODO handle newlines in filenames
manifest_file = os.fdopen(manifest_file_fd, 'r')
line_list = []
changed_file = False
for line in manifest_file:
    # remove trailing newline and add to list
    line = line[:-1]
    line_list.append(line)

    # wait for full record to be read
    if len(line_list) < 2: continue

    file_name1, file_name2 = line_list
    line_list = []

    changed_file = True
    vim_file.write('tabnew\n'
            'silent edit ' + file_name2 + '\n'
            'filetype detect\n'
            'silent diffsplit ' + file_name1 + '\n'
            'filetype detect\n')

vim_file.write('tabfirst\n')
vim_file.write('bd\n')
vim_file.close()

# if there was an incomplete record
if len(line_list):
    raise Error('Unexpected line(s):\n' + '\n'.join(line_list))

vim_rc = os.EX_OK
if changed_file:
    vim_rc = subprocess.call(['vim', '-R', '--cmd', 'au VimEnter * so ' + vim_file_name])

shutil.rmtree(temp_dir)
sys.exit(vim_rc)
