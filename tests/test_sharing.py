from urllib.parse import urlsplit,unquote
from PySide6.QtCore import QUrl
from netscan.core import Result
from netscan.sharing import make_links


def test_links_match_qurl_client_parser():
    r=Result('192.0.2.4:3128','192.0.2.0/24','OK',google='OK',example='OK',auth='Принята')
    link=make_links([r], 'a@b:/ю', 'p#?%:@/')
    q=QUrl(link)
    assert q.isValid() and q.host()=='192.0.2.4' and q.port()==3128
    assert q.userName()=='a@b:/ю' and q.password()=='p#?%:@/'
    assert q.fragment(QUrl.ComponentFormattingOption.FullyDecoded)=='NetScan 192.0.2.4:3128'


def test_only_working_deduplicated_no_unneeded_credentials():
    r=Result('192.0.2.4:3128','192.0.2.0/24','OK',google='OK',example='OK')
    bad=Result('192.0.2.5:3128','192.0.2.0/24','failed')
    text=make_links([r,bad,r],'secret-user','secret-password')
    assert text.count('http://')==1 and 'secret' not in text


def test_private_file_export(tmp_path):
    import os
    from netscan.sharing import write_links
    path=tmp_path/'links.txt';path.write_text('old');path.chmod(0o644)
    write_links(path,'http://test:password@192.0.2.4:3128')
    assert path.read_text().startswith('http://test:password@')
    if os.name!='nt': assert path.stat().st_mode & 0o777 == 0o600
