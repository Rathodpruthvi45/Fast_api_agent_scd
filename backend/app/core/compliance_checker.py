import subprocess
import winreg
from typing import Tuple
import os


class complince_check:
    def __init__(self):
        self.results = []

    def get_current_user_sid(self):
        try:
            cmd = "whoami /user"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            print("the result is ", result.stdout)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "S-1-5-21-" in line:
                        # Extract SID from the line
                        parts = line.split()
                        print(parts)
                        for part in parts:
                            if part.startswith("S-1-5-21-"):
                                return part
        except Exception as e:
            pass

        try:
            import getpass

            username = getpass.getuser()
            cmd = f'wmic useraccount where name="{username}" get sid /value'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            for line in result.stdout.split("\n"):
                if line.startswith("SID="):
                    return line.split("=")[1].strip()
        except:
            pass

        return None

    def normalize_registry_path(self, registry_path: str):
        """Normalize registry path and return (root_key, sub_key)."""
        registry_path = registry_path.replace("/", "\\")

        if registry_path.startswith("HKEY_LOCAL_MACHINE\\") or registry_path.startswith(
            "HKLM\\"
        ):
            root_key = winreg.HKEY_LOCAL_MACHINE
            sub_key = registry_path.replace("HKEY_LOCAL_MACHINE\\", "").replace(
                "HKLM\\", ""
            )
        elif registry_path.startswith(
            "HKEY_CURRENT_USER\\"
        ) or registry_path.startswith("HKCU\\"):
            root_key = winreg.HKEY_CURRENT_USER
            sub_key = registry_path.replace("HKEY_CURRENT_USER\\", "").replace(
                "HKCU\\", ""
            )
        elif registry_path.startswith("HKEY_USERS\\") or registry_path.startswith(
            "HKU\\"
        ):
            root_key = winreg.HKEY_USERS
            sub_key = registry_path.replace("HKEY_USERS\\", "").replace("HKU\\", "")
        elif registry_path.startswith("HKEY_CLASSES_ROOT\\"):
            root_key = winreg.HKEY_CLASSES_ROOT
            sub_key = registry_path.replace("HKEY_CLASSES_ROOT\\", "")
        else:
            root_key = winreg.HKEY_LOCAL_MACHINE
            sub_key = registry_path

        return root_key, sub_key

    def check_registry_value(self, key_path: str, value_name: str) -> tuple:
        """Check Windows registry value."""
        try:
            root_key, sub_key = self.normalize_registry_path(key_path)
            print(f"Checking registry: {key_path} -> {value_name}")

            with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ) as key:
                value, reg_type = winreg.QueryValueEx(key, value_name)
                return True, str(value)
        except FileNotFoundError:
            return False, f"Registry key/value not found: {key_path}\\{value_name}"
        except PermissionError:
            return False, f"Access denied to registry: {key_path}"
        except Exception as e:
            return False, f"Registry error: {str(e)}"

    def check_path_present(self, registry_key: str):
        root_key, sub_key = self.normalize_registry_path(registry_key)
        print(sub_key)
        print(winreg.HKEY_CURRENT_USER)

        try:
            if os.path.exists(registry_key):
                return True
            return False
        except Exception as e:
            print(e)
            return False

    def single_rule_check(self, rule):
        result = {
            "name": rule["name"],
            "description": rule["description"],
            "check_type": rule["check_type"],
            "registry_key": rule["registry_key"],
            "value_name": rule["value_name"],
            "expected_value": rule["expected_value"],
        }
        try:
            if rule["check_type"] == "registry":

                if rule["registry_key"]:
                    complinet = True
                    sucess, value = self.check_registry_value(
                        rule["registry_key"], rule["value_name"]
                    )
                    if sucess:
                        if value.strip() != str(rule["expected_value"]).strip():
                            complinet = False
                    else:
                        complinet = False
                        value = value  # error message
                    result["compliant"] = complinet
                    result["current_value"] = value

            return result
        except Exception as e:
            print(e)
            result["compliant"] = False
            result["current_value"] = None
            return result

    def check_all_rules(self, rules):
        try:

            for rule in rules:
                res = self.single_rule_check(rule)
                self.results.append(res)

            return self.results
        except Exception as e:
            print(e)


ComplianceChecker = complince_check()
