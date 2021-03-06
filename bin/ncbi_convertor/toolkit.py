import io
import json
import os
from os.path import abspath
from os.path import exists, dirname, join, expanduser

import pandas as pd
from Bio import Entrez
from ete3 import NCBITaxa
from tqdm import tqdm

from global_search.thirty_party.EntrezDownloader import EntrezDownloader
from global_search.thirty_party.metadata_parser import parse_bioproject_xml, parse_biosample_xml

ncbi = NCBITaxa()
taxons = ['superkingdom', 'phylum', 'class',
          'order', 'family', 'genus', 'species']

tmp_dir = '~/.tmp_getINFO'
tmp_dir = expanduser(tmp_dir)

import hashlib


def shash(astr):
    return hashlib.md5(astr.encode()).hexdigest()


def access_intermedia(obj, suffix='', redo=False):
    """
    It is mainly stodge intermediate result from previous results
    or provide a way to access it.
    Normally it should archive into current directory with md5 hashed file name.

    obj is necessary, normally it is a list of IDs/dictionary which also needed to generate md5 hashed file name.
    ofile is optional depend on what you want
    """
    nameofid = list(set(obj))
    _md5 = str(shash(';'.join(list(sorted(nameofid)))))
    ofile = join(tmp_dir, _md5) + '_' + suffix
    if not exists(dirname(ofile)):
        os.makedirs(dirname(ofile), exist_ok=1)
    if redo and exists(ofile):
        os.remove(ofile)
    if exists(ofile) and not redo:
        load_obj = json.load(open(ofile, 'r'))
        if isinstance(load_obj, dict):
            tqdm.write('Dectect same cache, use it instead of run it again.')
            return load_obj
    else:
        if isinstance(obj, list):
            # just used to validate run it yet?
            pass
        elif isinstance(obj, dict):
            json.dump(obj, open(ofile, 'w'))
        else:
            raise Exception('unexpected data type')


def parse_id(infile, columns=0):
    """
    1. format protein accession ID instead of using wrong one
    2. retrieving information provided inside the infile
    """
    id_list = []
    id2info = {}
    header_info = ''
    for row in tqdm(open(infile, 'r')):
        if row.startswith('#'):
            # header row
            header_info = row.strip('\n').strip('#').split('\t')
            continue
        if row:
            id = row.split('\t')[columns].strip().strip('\n')
            if '||' in id:
                id = id.split('||')[-1]
            id_list.append(id)
            if not header_info:
                id2info[id] = ';'.join(
                    row.split('\t')[columns + 1:]).strip('\n')
            else:
                id2info[id] = dict(zip(header_info[1:],
                                       row.strip('\n').split('\t')[columns + 1:]))
    return id_list, id2info


def unpack_gb(prot_t):
    """
    For standardizing unpack process from genbank formatted file
    """
    if not prot_t:
        return {}
    _cache_dict = {}
    annotations = prot_t.annotations
    ref_texts = [_
                 for _ in annotations.get('references', [])
                 if 'Direct' not in _.title and _.title]
    seq = str(prot_t.seq)
    org = annotations.get('organism', '')
    source = annotations.get('source', '')
    db_ = dict([_.split(':') for _ in prot_t.dbxrefs if ':' in _])
    biop = db_.get('BioProject', '')
    bios = db_.get('BioSample', '')
    nuccore_ID = annotations.get('db_source', '').split(' ')[-1]
    kw = ';'.join(annotations.get('keywords', []))
    comment = annotations.get('comment', '')
    for idx in range(10):
        if idx < len(ref_texts):
            ref_t = ref_texts[idx]
            _cache_dict[f'reference title {idx + 1}'] = ref_t.title
            _cache_dict[f'reference journal {idx + 1}'] = ref_t.journal
            _cache_dict[f'reference authors {idx + 1}'] = ref_t.authors
    _cache_dict['organism'] = org
    _cache_dict['sequence'] = seq
    _cache_dict['source'] = source
    _cache_dict['bioproject'] = biop
    _cache_dict['biosample'] = bios
    _cache_dict['nuccore ID'] = nuccore_ID
    _cache_dict['keyword'] = kw
    _cache_dict['comment'] = comment
    return _cache_dict


edl = EntrezDownloader(
    # An email address. You might get blocked by the NCBI without specifying one.
    email='l0404th@gmail.com',
    # An API key. You can obtain one by creating an NCBI account. Speeds things up.
    api_key='ccf9847611deebe1446b9814a356f14cde08',
    num_threads=30,  # The number of parallel requests to make
    # The number of IDs to fetch per request
    batch_size=50,
    pbar=True  # Enables a progress bar, requires tqdm package
)


def tax2tax_info(taxid):
    lineage = ncbi.get_lineage(int(taxid))
    rank = ncbi.get_rank(lineage)
    rank = {v: k for k, v in rank.items()}
    names = ncbi.get_taxid_translator(lineage)
    _dict = {}
    for c in taxons:
        if c in rank:
            _dict[c] = names[rank[c]]
    return _dict


def process_path(path):
    if not '/' in path:
        path = './' + path
    if path.startswith('~'):
        path = expanduser(path)
    if path.startswith('.'):
        path = abspath(path)
    return path


def parse_ipg(t):
    """
    parse result efetched from Identical Protein Groups(ipg)
23582877        INSDC   HQ650005.1      1       452     +       AEG74045.1      ammonia monooxygenase subunit alpha     uncultured bacterium
186872893       INSDC   MG992186.1      1       531     +       AWG96903.1      particulate methane monooxygenase subunit A     uncultured bacterium
    :param t:
    :return:
    """
    bucket = []
    whole_df = pd.read_csv(io.StringIO(t), sep='\t', header=None)
    gb = whole_df.groupby(0)
    all_dfs = [gb.get_group(x) for x in gb.groups]
    for indivi_df in all_dfs:
        indivi_df.index = range(indivi_df.shape[0])
        # aid = indivi_df.iloc[0, 6]
        indivi_df = indivi_df.fillna('')
        pos = [(row[2], row[3], row[4], row[5])
               for row in indivi_df.values]
        gb = [row[10]
              for row in indivi_df.values]
        for row in indivi_df.values:
            bucket.append((row[6], pos, gb))
    return bucket


def get_bioproject(bp_list):
    results, failed = edl.esearch(db='bioproject',
                                  ids=bp_list,
                                  result_func=lambda x: Entrez.read(io.StringIO(x))['IdList'])
    all_GI = results[::]
    results, failed = edl.efetch(db='bioproject',
                                 ids=all_GI,
                                 retmode='xml',
                                 retype='xml',
                                 result_func=lambda x: parse_bioproject_xml(x))
    bp2info = {}
    for _ in results:
        if isinstance(_, dict):
            bp2info.update(_)
    return bp2info


def get_biosample(bs_list):
    results, failed = edl.esearch(db='biosample',
                                  ids=bs_list,
                                  result_func=lambda x: Entrez.read(io.StringIO(x))['IdList'])
    all_GI = results[::]
    results, failed = edl.efetch(db='biosample',
                                 ids=all_GI,
                                 retmode='xml',
                                 retype='xml',
                                 result_func=lambda x: parse_biosample_xml(x))
    bs2info = {}
    for _ in results:
        if isinstance(_, dict):
            bs2info.update(_)
    return bs2info
