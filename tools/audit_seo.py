"""Release checks for representative search landing pages; never claims Google indexing."""
import json,re
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
def main():
    manifest=json.loads((SITE/'build-manifest.json').read_text(encoding='utf-8'))
    paths=manifest['indexable'];examples=['/','/players/','/matches/','/records/','/compare/','/studio/','/data-coverage/','/datasets/','/research/']
    for prefix in ('/players/','/records/men/','/records/women/','/research/','/compare/','/questions/how-many-','/teams/','/grounds/'):
        examples.extend([p for p in paths if p.startswith(prefix) and p!=prefix][:2])
    for path in set(examples):
        text=(SITE/path.strip('/')/'index.html').read_text(encoding='utf-8')
        assert len(re.findall(r'<h1(?:\s[^>]*)?>',text))==1,path
        assert f'href="https://cricket.rkjat.in{path}"' in text,path
        assert '<meta name="description"' in text,path
        assert 'index,follow,max-image-preview:large' in text,path
        assert 'name="viewport"' in text,path
        schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',text).group(1))
        if path!='/':assert schema['breadcrumb']['@type']=='BreadcrumbList',path
        if path.startswith('/players/') and path.count('/')>=3:
            assert schema['breadcrumb']['itemListElement'][1]['name']=='Players',path
            assert 'career-stat-grid' not in text,path
            assert 'id="career-records"' in text,path
            desc=re.search(r'<meta name="description" content="([^"]*)"',text).group(1)
            if 'no matched career record' in text:
                assert 'Batting career records by format' not in text,path
            else:
                assert re.search(r'\d', desc),path
                assert 'Batting career records by format' in text,path
        if path.startswith('/questions/how-many-'):
            assert 'FAQPage' in text,path
            qdesc=re.search(r'<meta name="description" content="([^"]*)"',text).group(1)
            assert re.search(r'\d', qdesc),path
            assert 'question-hero' in text,path
        if path.startswith('/teams/') and path.count('/')>=3:
            tdesc=re.search(r'<meta name="description" content="([^"]*)"',text).group(1)
            assert re.search(r'\d', tdesc),path
            assert 'career-glance' in text,path
            assert 'FAQPage' in text,path
        if path.startswith('/grounds/') and path.count('/')>=3:
            assert 'career-glance' in text or 'venue-conditions' in text,path
        if path=='/datasets/':assert schema['@type']=='Dataset' and len(schema['distribution'])==4
    report={'passed':True,'representative_pages_checked':len(set(examples)),'sitemap_indexable_pages':len(paths),'titles_unique':len(set(p['title'] for p in paths.values()))==len(paths),'indexing_status':'Unknown: Google Search Console access required','field_core_web_vitals':'Not measured: requires real visitor data','advertising':'No ad network enabled; no audience claims'}
    (SITE/'seo-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
