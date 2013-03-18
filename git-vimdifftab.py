#!/usr/bin/python

# Use vimdiff with git, diffing each file in its own tab.
# @author Chris Pick <vimdifftab@chrispick.com>
# @section LICENSE
#
# Copyright 2012 Chris Pick. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY CHRIS PICK ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL CHRIS PICK OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of Chris Pick.


import sys, subprocess, os, os.path, tempfile, shutil

def copy_if_tmp(file_dir, file_name):
    # files that look like temp files need to be copied
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
    sys.exit('Script must be called dirctly, not run from interpreter')

git_diff_rc = subprocess.call(
    ['git', 'difftool', '--no-prompt',
            '--extcmd=' + script_name] + sys.argv[1:])
if git_diff_rc != os.EX_OK:
    sys.exit('git difftool failed: ' + str(git_diff_rc))

vim_file_fd, vim_file_name = tempfile.mkstemp('.vim', '', temp_dir, True)
vim_file = os.fdopen(vim_file_fd, 'a')

repo_root_rel = subprocess.check_output(['git', 'rev-parse',
        '--show-cdup']).strip()
def adjust_relative_path(root, path):
    if os.path.isabs(path):
        return path

    return os.path.join(root, path)

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

    file_name1 = adjust_relative_path(repo_root_rel, file_name1)
    file_name2 = adjust_relative_path(repo_root_rel, file_name2)

    changed_file = True
    vim_file.write('tabnew\n'
            'silent edit ' + file_name2 + '\n'
            'filetype detect\n'
            'silent vertical diffsplit ' + file_name1 + '\n'
            'filetype detect\n')

vim_file.write('tabfirst\n')
vim_file.write('bd\n')
vim_file.close()

# if there was an incomplete record
if len(line_list):
    sys.exit('Unexpected line(s):\n' + '\n'.join(line_list))

vim_rc = os.EX_OK
if changed_file:
    vim_rc = subprocess.call(['vim', '-R', '--cmd', 'au VimEnter * so ' + vim_file_name])

shutil.rmtree(temp_dir)
sys.exit(vim_rc)
