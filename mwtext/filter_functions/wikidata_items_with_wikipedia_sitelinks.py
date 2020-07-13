import json
import requests
from collections import defaultdict

import mwbase
import mwapi

from ..utilities.util import get_siteinfo

def get_wiki_languages():
    session = mwapi.Session("https://commons.wikimedia.org", user_agent = "")
    doc = session.get(action="sitematrix", smtype="language")
    sitematrix = doc['sitematrix']

    lang_wiki = defaultdict(str)
    for lang in sitematrix.keys():
        if not lang.isdigit():
            continue

        lang_code = sitematrix[lang].get('code')
        site = sitematrix[lang].get('site')
        wiki_host = ''
        for s in site:
            if s.get('code', None) == "wiki" and s.get('closed', None) is None:
                wiki_host = s.get('url')
        if wiki_host:
            lang_wiki[lang_code + "wiki"] = wiki_host

    return lang_wiki


def get_namespace_names():
    languages = get_wiki_languages()
    namespace_names = defaultdict(list)
    for lang in languages:
        session = mwapi.Session(languages[lang], user_agent = "")
        doc = get_siteinfo(session)
        namespaces = doc['namespaces']
        for n in namespaces:
            if namespaces[n].get('id') == 0:
                continue
            namespace_name = namespaces[n].get('name')
            namespace_names[lang].append(namespace_name)

    return namespace_names

namespace_names = get_namespace_names()


def include(page, revision):
    # Namespace zero
    if page.namespace != 0 or revision.model != 'wikibase-item':
        return False

    item_doc = json.loads(revision.text)
    qid = item_doc.get('id', None)
    entity = mwbase.Entity.from_json(item_doc)

    # Has a Qid
    if qid is None:
        return False

    # Sitelinks to a Wikipedia article
    for llink in entity.sitelinks:
        if llink not in namespace_names:
            continue

        title = entity.sitelinks[llink].get('title')
        is_article = not any(title.startswith(restricted_namespace + ":")
                         for restricted_namespace in namespace_names[llink])
        if is_article:
            return True

    return False
