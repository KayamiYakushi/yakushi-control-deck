from __future__ import annotations

import shlex
import shutil
from pathlib import Path

from .history import record
from .io import run
from .paths import POWER_STATE

CPUFREQ = Path('/sys/devices/system/cpu/cpufreq')


def _read(path: Path, default: str = '') -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return default


def _policy_dirs() -> list[Path]:
    if not CPUFREQ.exists():
        return []
    return sorted(path for path in CPUFREQ.glob('policy*') if path.is_dir())


def _words(path: Path) -> list[str]:
    return [item for item in _read(path).split() if item]


def _powerprofiles_status() -> dict | None:
    if not shutil.which('powerprofilesctl'):
        return None

    proc = run(['powerprofilesctl', 'get'], timeout=4.0)
    if proc.returncode != 0:
        return None

    profile = proc.stdout.strip()
    if not profile:
        return None

    return {
        'backend': 'power-profiles-daemon',
        'profile': profile,
        'mode': 'performance' if profile == 'performance' else 'balanced',
    }


def status() -> dict:
    ppd = _powerprofiles_status()
    policies = _policy_dirs()
    policy = policies[0] if policies else None

    driver = _read(policy / 'scaling_driver') if policy else ''
    governor = _read(policy / 'scaling_governor') if policy else ''
    governors = _words(policy / 'scaling_available_governors') if policy else []
    epp = _read(policy / 'energy_performance_preference') if policy else ''
    epp_available = _words(policy / 'energy_performance_available_preferences') if policy else []

    if ppd:
        mode = ppd['mode']
        backend = ppd['backend']
        profile = ppd['profile']
    else:
        performance_epp = epp == 'performance'
        mode = 'performance' if governor == 'performance' and (not epp or performance_epp) else 'balanced'
        backend = 'CPUFreq / AMD P-State' if policy else 'Unavailable'
        profile = ''

    return {
        'supported': bool(ppd or policy),
        'backend': backend,
        'profile': profile,
        'mode': mode,
        'driver': driver or 'Unknown',
        'governor': governor or 'Unknown',
        'available_governors': governors,
        'epp': epp or 'Not exposed',
        'available_epp': epp_available,
    }


def _write_legacy_indicator(mode: str) -> None:
    value = 'performance\n' if mode == 'performance' else 'balanced\n'
    try:
        POWER_STATE.parent.mkdir(parents=True, exist_ok=True)
        POWER_STATE.write_text(value)
    except OSError:
        pass


def _direct_cpufreq(mode: str, current: dict) -> tuple[bool, str]:
    policies = _policy_dirs()
    if not policies:
        return False, 'CPU frequency controls are not exposed by the kernel.'

    governors = current.get('available_governors', [])
    epp_available = current.get('available_epp', [])

    if mode == 'performance':
        governor = 'performance' if 'performance' in governors else (governors[0] if governors else '')
        epp = 'performance' if 'performance' in epp_available else ''
    else:
        if 'schedutil' in governors:
            governor = 'schedutil'
        elif 'powersave' in governors:
            governor = 'powersave'
        else:
            governor = governors[0] if governors else ''

        if 'balance_performance' in epp_available:
            epp = 'balance_performance'
        elif 'balance_power' in epp_available:
            epp = 'balance_power'
        elif 'power' in epp_available:
            epp = 'power'
        else:
            epp = ''

    if not governor:
        return False, 'No usable CPU frequency governor was reported by the kernel.'

    if not shutil.which('pkexec'):
        return False, 'Polkit pkexec is unavailable, so privileged CPU controls cannot be changed safely.'

    governor_q = shlex.quote(governor)
    epp_q = shlex.quote(epp)

    script = [
        'set -eu',
        'for p in /sys/devices/system/cpu/cpufreq/policy*; do',
        '  [ -e "$p/scaling_governor" ] && printf %s ' + governor_q + ' > "$p/scaling_governor"',
    ]
    if epp:
        script.append('  [ -e "$p/energy_performance_preference" ] && printf %s ' + epp_q + ' > "$p/energy_performance_preference" || true')
    script.append('done')

    proc = run(['pkexec', 'sh', '-c', '\n'.join(script)], timeout=30.0)
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout).strip()
        return False, message or 'The privileged CPU power change was cancelled or rejected.'

    return True, (
        f'Performance mode applied ({governor}).'
        if mode == 'performance'
        else f'Balanced mode applied ({governor}{" / " + epp if epp else ""}).'
    )


def apply_mode(mode: str, *, record_history: bool = True) -> tuple[bool, str]:
    if mode not in {'balanced', 'performance'}:
        return False, 'Unknown power mode.'

    before = status()
    if not before.get('supported'):
        return False, 'No supported power-management backend was detected.'

    if record_history:
        record(
            'Power mode',
            runtime={
                'kind': 'power_mode',
                'values': {'mode': before.get('mode', 'balanced')},
            },
        )

    if before.get('backend') == 'power-profiles-daemon':
        profile = 'performance' if mode == 'performance' else 'balanced'
        proc = run(['powerprofilesctl', 'set', profile], timeout=15.0)
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout).strip()
            return False, message or f'Could not switch to {profile}.'
        _write_legacy_indicator(mode)
        return True, f'{profile.title()} power profile applied.'

    ok, message = _direct_cpufreq(mode, before)
    if ok:
        _write_legacy_indicator(mode)
    return ok, message
