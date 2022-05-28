import re
from collections import defaultdict

class MaterialRules:
    def __init__(self, merchant):
        self.merchant = merchant

    def __call__(self, row):
        return self.post_process(getattr(self, self.merchant)(row))

    def post_process(self, attr_dict):
        if attr_dict:
            for key, val in attr_dict.items():
                if isinstance(val, list):
                    val = ",".join(val)
                val = re.sub(r"[0-9%]", "", val)
                val = re.sub(r"[\s]{2:}", " ", val)
                attr_dict[key] = val
            return attr_dict

    def all_sole(self, row):
        if material_str := row["Fashion:material"]:
            attrs = re.findall(r"[A-z][\w]+: [^.]+\.", material_str)
            attr_dict = {}
            for attr in attrs:
                attr = attr[:-1].lower().split(": ")
                attr_dict[attr[0]] = attr[1]
            return attr_dict

    def begg_shoes(self, row):
        if material := row["Fabric"]:
            return {"material": material.strip().lower()}

    def converse(self, row):
        if material := row["Fashion:material"]:
            return {"material": material.strip().lower().split(", ")}

    def deichmann(self, row):
        if material := row["short_description"]:
            attrs = re.findall(r"[A-Z][ \w&]+: [^A-Z]+", material)
            attr_dict = {}
            for attr in attrs:
                attr = attr.strip().lower().split(": ")
                attr_dict[attr[0]] = attr[1]
            return attr_dict

    def foot_locker(self, row):
        if material := row["Fashion:material"]:
            return {"material": material.strip().lower().split("/")}

    def secret_sales(self, row):
        if material := row["specifications"]:
            return {"material": str().strip().lower()}

    def standout(self, row):
        if material_str := row["Fashion:material"]:
            if ":" in material_str and "/" in material_str:
                attrs = material_str.split("/")
                attr_dict = {}
                for attr in attrs:
                    attr = attr.lower().strip().split(": ")
                    attr_dict[attr[0]] = attr[1]
                return attr_dict
            if "/" in material_str and not ":" in material_str:
                return {"material": material_str.lower().strip().split("/")}
            if (
                "," in material_str
                and not ":" in material_str
                and not "/" in material_str
            ):
                return {"material": material_str.lower().strip().split(",")}

    def choice(self, row):
        if material_str := row["Fashion:material"]:
            material_str = re.sub(
                r"(Wipe|Spot|Pre-Treat|Pre treat|care).+$",
                "",
                material_str,
                flags=re.IGNORECASE,
            )
            matches = list(
                re.finditer(r"(Upper|Sole|Lining|Insole|Footbed|Outer): ", material_str)
            )
            attr_dict = {}
            for i in range(len(matches)):
                attr_dict[matches[i].group().strip().lower()[:-1]] = (
                    re.sub(
                        r"[^A-Za-z]+",
                        " ",
                        material_str[
                            matches[i].end() : matches[i + 1].start()
                            if i + 1 < len(matches)
                            else None
                        ],
                    )
                    .replace(" ", " ")
                    .strip()
                    .lower()
                )
            return attr_dict

    def size(self, row):
        if material_str := row["Fashion:material"]:
            material_str = material_str.lower().strip()
            if (
                "/" in material_str
                and "upper" in material_str
                and "sole" in material_str
            ):
                upper, sole = re.sub(r"(upper|sole)", "", material_str).split("/")
                return {"upper": upper, "sole": sole}
            elif "/" in material_str:
                return {"material": material_str.split("/")}
            else:
                return {"material": material_str}

    def under_armour(self, row):
        if material_str := row["keywords"].lower().strip():
            upper, sole = material_str.split("~")
            upper = upper.replace("upper:", "").strip()
            sole = sole.replace("outsole:", "").strip()
            return {"upper": upper, "sole": sole}

    def stadium_goods(self, row):
        if material_str := row["material"]:
            return {"material": material_str.lower().strip().split("/")}

    def daniel_footwear(self, row):
        if material := row["material"]:
            return {"material": material}

    def blue_tomato(self, row):
        if material_str := row["custom_5"]:
            if ":" not in material_str:
                return {"material": material_str.lower().strip().split(", ")}

    def jd_sports(self, row):
        if material_str := row["Fashion:material"]:
            attr_dict = defaultdict(list)
            capture_groups = ("upper", "sole", "lining")
            material_str = re.sub(r"[0-9%]", "", material_str.lower().strip())
            material_str = material_str.replace("& ", ",")
            tokens = re.split(r"[,\/\.]", material_str)
            for token in tokens:
                for group in capture_groups:
                    if group in token:
                        attr_dict[group].append(
                            token.replace(group, "").replace(":", "").strip()
                        )
                        break
                else:
                    attr_dict["material"].append(token)
        return attr_dict
