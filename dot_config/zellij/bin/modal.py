"""Search-first fzf picker with explicit navigation and cancellation keys."""
import subprocess


def pick(lines, header, extra=(), key_actions=None, preview=None, ansi=False, header_lines=0):
    bindings = ['ctrl-j:down', 'ctrl-k:up', 'ctrl-d:half-page-down',
                'ctrl-u:half-page-up', 'esc:abort']
    bindings += ['alt-' + key + ':print(@' + key + ')+accept' for key in extra]
    bindings += [key + ':print(@' + action + ')+accept' for key, action in (key_actions or {}).items()]
    args = ['fzf', '--no-sort', '--reverse', '--no-exit-0', '--no-select-1', '--delimiter=\t',
            '--with-nth=2..', '--prompt=Search> ', '--header=' + header + '\n↑/↓ or Ctrl+J/K move · type to search · Esc cancel',
            '--padding=1,2', '--info=inline-right', '--pointer=›', '--no-scrollbar',
            # NO_COLOR selects fzf's bw base, whose strip attribute removes input ANSI.
            # Agent pickers explicitly opt into color; other menus keep their behavior.
            '--color=' + ('dark,' if ansi else '') + 'bg:-1,fg:#d5c8ac,bg+:#30302e,fg+:#d5c8ac,hl:#c19d7a,hl+:#c19d7a,pointer:#d5c8ac,prompt:#d5c8ac,header:#96a3ab,info:#96a3ab',
            '--bind=' + ','.join(bindings)]
    if ansi:
        args += ['--ansi']
    if header_lines:
        args += ['--header-lines=' + str(header_lines)]
    if preview:
        args += ['--preview=' + preview, '--preview-window=down,30%,border-top']
    result = subprocess.run(args, input='\n'.join(lines) + ('\n' if lines else ''), text=True, stdout=subprocess.PIPE)
    if result.returncode in (1, 130):
        return None, None
    if result.returncode:
        raise RuntimeError('Workspace picker failed')
    output = result.stdout.splitlines()
    action = output.pop(0)[1:] if output and output[0].startswith('@') else ''
    return (output[0], action) if output else (None, None)
