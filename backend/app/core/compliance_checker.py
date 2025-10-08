

import subprocess

class complince_check:
    def __init__(self):
        pass

    def get_current_user_sid(self):
        try:
            cmd = 'whoami /user'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            print("the result is ",result.stdout)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'S-1-5-21-' in line:
                        # Extract SID from the line
                        parts = line.split()
                        print(parts)
                        for part in parts:
                            if part.startswith('S-1-5-21-'):
                                return part
        except Exception as e:
            pass

        try:
            import getpass
            username = getpass.getuser()
            cmd = f'wmic useraccount where name="{username}" get sid /value'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if line.startswith('SID='):
                    return line.split('=')[1].strip()
        except:
            pass
            
        return None

ComplianceChecker=complince_check()