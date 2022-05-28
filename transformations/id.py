import os
import re
import string
import hashlib
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse
from attr import has

import pandas as pd


def hash_url(url):
    """Hash a url to be used as a unique identifier for offer_ids

    Args:
        url: String of the url to be hashed
    Returns:
        String of the hashed url
    """
    return f"{hashlib.md5(url.encode('utf-8')).hexdigest()[:25]}"


def make_offer_id(offer_id, merchant_name):
    """Build the offer_id used to uniquely identify offers in the database and S3
    Args:
        offer_id: Unique identifies for the offer
        merchant_name: Merchant name
    Returns:
        String
    Raises:
        Generic Exception
    """
    if pd.isna(offer_id) or offer_id is None:
        raise Exception("Invalid offer_id (NA or NULL)")
    elif merchant_name == "" or merchant_name is None:
        raise Exception("Invalid mercant_name (empty or NULL)")
    else:
        offer_id = "".join(
            [
                char
                for char in str(offer_id)
                if char in string.ascii_letters + string.digits
            ]
        )
        merchant_name = str(merchant_name).replace(" ", "_").lower()
        return f"{merchant_name}.{offer_id}"


class IDRules:
    def __init__(self, config, merchant):
        self.config = config
        self.merchant = merchant

    def __call__(self, row):
        if hasattr(self, self.merchant):
            return getattr(self, self.merchant)(row)
        else:
            return make_offer_id(row[self.config.pid[self.merchant]], self.merchant)

    def nike(self, row):
        return make_offer_id(
            offer_id=hash_url(row["merchant_deep_link"]),
            merchant_name=self.merchant,
        )

    def choice(self, row):
        decoded = unquote(row["merchant_deep_link"])
        id_in_qs = decoded.rsplit("/", 2)[1]
        return make_offer_id(
            offer_id=id_in_qs,
            merchant_name=self.merchant,
        )

    def ellesse(self, row):
        """
        Ellese urls include the product line plus variant
        We can extract the relevant parts to create a new url to hash
        """
        encoded = urlparse(row["merchant_deep_link"])
        product_line = encoded.path.rsplit("/", 1)[0]
        url = urlunparse((encoded.scheme, encoded.netloc, product_line, "", "", ""))
        return make_offer_id(
            offer_id=hash_url(url),
            merchant_name=self.merchant,
        )

    def footpatrol(self, row):
        """
        URL is wrapped around cookie tracking
        use parse_qs to extract the product page url (destinationUrl)
        a unique id is extract from the parsed destinationUrl
        Same platform as Size
        """
        parsed_url = urlparse(row["merchant_deep_link"])
        qs_prep = parse_qs(parsed_url.query)["destinationUrl"]
        product_id = qs_prep[0].split("/")[-2].replace("footpatrolcom", "")
        return make_offer_id(
            offer_id=product_id,
            merchant_name=self.merchant,
        )

    def sevenstore(self, row):
        """
        sevenstore "merchant deep links" contain product line + variants
        this can be used to generate a hash for a uniqure
        groupby id
        """
        url = row["merchant_deep_link"]
        return make_offer_id(
            offer_id=hash_url(url),
            merchant_name=self.merchant,
        )

    def size(self, row):
        """
        URL is wrapped around cookie tracking
        use parse_qs to extract the product page url (destinationUrl)
        a unique id is extract from the parsed destinationUrl
        Same platform as Foot Asylum
        """
        parsed_url = urlparse(row["merchant_deep_link"])
        qs_prep = parse_qs(parsed_url.query).get("destinationUrl", None)
        if qs_prep:
            product_id = qs_prep[0].split("/")[-2]
            return make_offer_id(
                offer_id=product_id,
                merchant_name=self.merchant,
            )

    def very(self, row):
        return make_offer_id(
            offer_id=hash_url(row["merchant_deep_link"]),
            merchant_name=self.merchant,
        )

    def under_armour(self, row):
        url = row["merchant_deep_link"]
        regex = r"(.*?)(&.*)?"
        id_in_path = re.sub(regex, r"\1", url)
        return make_offer_id(
            offer_id=hash_url(id_in_path),
            merchant_name=self.merchant,
        )

    def reebok(self, row):
        """
        Reebok does not contain grouping IDs in the feed.
        Product ID column can split on the dash, and retain the left side.
        """
        prod_id = row["Product ID"]
        split_id = prod_id.split("-")[0]
        return make_offer_id(
            offer_id=split_id,
            merchant_name=self.merchant,
        )

    def daniel_footwear(self, row):
        """
        Merchant does not use distinct grouping ids.
        We can find the id in the row['link'] column.
        Example https://prf.hn/click/camref:1101ldMaK/creativeref:1100l75000/destination:https://www.danielfootwear.com/ugg-scuffette-p18934/s116139?cid=GBP&glCurrency=GBP&glCountry=GB&pk_cid=6&pk_keyword=116139&pk_medium=multifeeds&pk_campaign=PartnerizeUK&pk_source=PartnerizeUK&pk_content=ClothingAccessoriesShoes&utm_source=Partnerize+UK

        ugg-scuffette-p18934 this part can be extracted to generate an offer id hash.
        """
        decoded = urlparse(row["link"]).path
        regex = r"(?<=https:\/\/www.danielfootwear.com).*"
        id_in_path = re.findall(regex, decoded)[0]
        prod_line_and_variant_extracted = id_in_path.rsplit("/", 1)[0]
        return make_offer_id(
            offer_id=prod_line_and_variant_extracted,
            merchant_name=self.merchant,
        )

    def brother2brother(self, row):
        """
        Brother2Brother does not use distinct grouping ids.
        The LINK column contains distinct product lines + variants

        I tried at first to extract black-leather-clean-90-trainer-p18029
        From https://prf.hn/click/camref:1101leurc/creativeref:1011l46253/destination:https://www.brother2brother.co.uk/men-c163/footwear-c6/black-leather-clean-90-trainer-p18029/s134581?utm_medium=organic&utm_term=axel-arigato-black-leather-clean-90-trainer-size-uk-9-size-uk-9-14996-21124181&utm_campaign=froogle&cid=GBP

        However the URLs hae a small portion which are inconsistent generating out of index range errors.

        Instead we can extract the p{digits} syntax to generate IDs
        """
        decoded = urlparse(row["LINK"]).path
        regex = r"(?<=https:\/\/www.brother2brother.co.uk/).*"
        id_in_path = re.findall(regex, decoded)[0]
        id_regex = r"(p\d{4,})"
        prod_line_and_variant_extracted = re.findall(id_regex, id_in_path)
        return make_offer_id(
            offer_id=prod_line_and_variant_extracted,
            merchant_name=self.merchant,
        )

    def cho(self, row):
        try:
            colour = row["COLOR"]
            decoded = urlparse(row["LINK"]).path
            regex = r"(?<=https:\/\/www.cho.co.uk\/).*"
            id_in_path = re.findall(regex, decoded)[0]
            extract_id = r"(p\d{4,})"
            variant_id = re.findall(extract_id, id_in_path)[0]

            return make_offer_id(
                offer_id=f"{colour}.{variant_id}",
                merchant_name=self.merchant,
            )
        except Exception:
            return None

    def excell_sports(self, row):
        """
        Excel sports have the offer_id in the URL
        They break out variants into distinct p values
        is the rule "-p{digits}"
        """
        decoded = urlparse(row["LINK"]).path

        regex = r"(?<=https:\/\/www.excell-sports.com/).*"
        id_in_path = re.findall(regex, decoded)[0]
        id_regex = r"(-p\d{4,})"
        prod_line_and_variant_extracted = re.findall(id_regex, id_in_path)

        return make_offer_id(
            offer_id=prod_line_and_variant_extracted,
            merchant_name=self.merchant,
        )
