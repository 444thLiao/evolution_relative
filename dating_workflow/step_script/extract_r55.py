import multiprocessing as mp
import os
from collections import defaultdict
from glob import glob
from os.path import *
from subprocess import check_call

import click
from Bio import SeqIO
from tqdm import tqdm

from dating_workflow.step_script import parse_blastp

rbp_db = "/home-user/thliao/data/protein_db/rbp55"

__file__ = '/home-user/thliao/script/evolution_relative/dating_workflow/step_script/extrat_r55.py'
r55_list = join(dirname(__file__), 'Rbp55.tsv')
rbp55_id_list = [row.split('\t')[0] for row in open(r55_list) if row.split('\t')[0]]


# ABOVE is the default setting for luolab server.

# TIGRFAM_db = f"{resource_dir}/TIGRFAM_v14/TIGR00487.HMM"
# ABOVE is the default setting for luolab server.

def run(cmd):
    check_call(cmd,
               shell=True,
               stdout=open('/dev/null', 'w'),
               stderr=open('/dev/null', 'w'))


def annotate_cog(protein_file_list, cog_out_dir):
    params = []
    for f in protein_file_list:
        gname = basename(f).replace('.faa', '')
        # for cdd
        ofile = f'{cog_out_dir}/Rbp55/{gname}.out'
        cmd = f"/home-user/software/blast/latest/bin/rpsblast -query {f} -db {rbp_db} -max_target_seqs 1 -num_threads 10 -outfmt 6 -evalue 1e-3  -out {ofile}"
        if not os.path.exists(ofile):
            if not exists(dirname(ofile)):
                os.makedirs(dirname(ofile))
            params.append(cmd)

    with mp.Pool(processes=5) as tp:
        list(tqdm(tp.imap(run, params), total=len(params)))


def parse_annotation(cog_out_dir, top_hit=False, evalue=1e-3):
    # for cdd
    # _cdd_match_ids = set([_ for vl in cdd_num.values() for _ in vl])
    genome2cdd = defaultdict(lambda: defaultdict(list))

    # cdd annotations
    tqdm.write('start to read/parse output files')
    cdd_anno_files = glob(join(cog_out_dir, '*.out'))
    for ofile in tqdm(cdd_anno_files):
        gname = basename(ofile).replace('.out', '')
        locus_dict = parse_blastp(ofile=ofile,
                                  match_ids=[],
                                  top_hit=top_hit,
                                  filter_evalue=evalue)
        genome2cdd[gname].update(locus_dict)
    return genome2cdd


# extract protein
def write_cog(outdir, genome2cdd, raw_proteins, genome_ids=[], get_type='prot'):
    genome2seq = {}
    if not genome_ids:
        genome_ids = list(genome2cdd)
    gene_ids = set([_ for vl in genome2cdd.values() for _ in vl])
    pdir = dirname(expanduser(raw_proteins))
    if get_type == 'nuc':
        suffix = 'ffn'
    elif get_type == 'prot':
        suffix = 'faa'
    else:
        raise Exception
    if not exists(outdir):
        os.makedirs(outdir)
    tqdm.write('get sequence file')
    for genome_name in tqdm(genome_ids):
        g_dict = genome2cdd[genome_name]
        gfile = f'{pdir}/{genome_name}.faa'
        new_pdir = abspath(dirname(dirname(realpath(gfile))))
        if suffix == 'faa':
            # important bugs!!!!! fixed
            new_gfile = gfile
        else:
            new_gfile = f"{new_pdir}/tmp/{genome_name}/{genome_name}.{suffix}"

        if exists(new_gfile):
            _cache = {record.id: record
                      for record in SeqIO.parse(new_gfile, format='fasta')}
            seq_set = {k: [_cache[_]
                           for _ in v
                           if _ in _cache]
                       for k, v in g_dict.items()}
            genome2seq[genome_name] = seq_set
        else:
            # not with prokka annotations
            print('not annotated with prokka')
            if not gfile.endswith(suffix):
                print(f'not {suffix},past it')
                continue
            _cache = {record.id: record
                      for record in SeqIO.parse(gfile, format='fasta')}
            seq_set = {k: [_cache[_]
                           for _ in v
                           if _ in _cache]
                       for k, v in g_dict.items()}
            genome2seq[genome_name] = seq_set

    # concat/output proteins
    tqdm.write('write out')
    for each_gene in tqdm(gene_ids):
        gene_records = []
        for gname, seq_dict in genome2seq.items():
            get_records = seq_dict.get(each_gene, [])
            for record in get_records:
                record.name = gname
            gene_records += get_records
        unique_cdd_records = []
        [unique_cdd_records.append(record)
         for record in gene_records
         if record.id not in [_.id
                              for _ in unique_cdd_records]]

        with open(join(outdir, f"{each_gene.replace('CDD:', '')}.faa"), 'w') as f1:
            SeqIO.write(unique_cdd_records, f1, format='fasta-2line')


def stats_cog(genome2genes, gene_ids):
    gene_multi = {g: 0 for g in gene_ids}
    for genome, pdict in genome2genes.items():
        for gene, seqs in pdict.items():
            if len(seqs) >= 2:
                gene_multi[gene] += 1
    gene_Ubiquity = {g: 0 for g in gene_ids}
    for genome, pdict in genome2genes.items():
        for gene, seqs in pdict.items():
            gene_Ubiquity[gene] += 1

    gene2genome_num = {}
    gene2genomes = {}
    for gene in gene_ids:
        _cache = [k for k, v in genome2genes.items() if v.get(gene, [])]
        # for genome, pdict in genome2genes.items():
        gene2genome_num[gene] = len(_cache)
        gene2genomes[gene] = _cache
    return gene_multi, gene_Ubiquity, gene2genome_num, gene2genomes


@click.command()
@click.option("-in_p", 'in_proteins', help='input directory which contains protein sequences file')
@click.option("-in_a", 'in_annotations', help="Actually output directory which contains annotations files during extraction")
@click.option("-s", "suffix", default='faa', help='suffix of protein files in `in_p`')
@click.option("-o", 'outdir', help="name of output directory")
@click.option("-evalue", 'evalue', default=1e-50, help="evalue for filtering out false-positive proteins. default is 1e-50 ")
@click.option("-gl", "genome_list", default=None,
              help="It will read 'selected_genomes.txt', please prepare the file, or indicate the alternative name or path. It could be None. If you provided, you could use it to subset the aln sequences by indicate names.")
def main(in_proteins, suffix, in_annotations, outdir, evalue, genome_list):
    if genome_list is None:
        gids = []
    else:
        gids = open(genome_list).read().split('\n')
        gids = list(set([_ for _ in gids if _]))
    in_proteins = join(in_proteins, '*.' + suffix.strip('.'))
    protein_files = glob(in_proteins)
    if not protein_files:
        exit(f"error input proteins dir {in_proteins}")
    if not exists(in_annotations):
        os.makedirs(in_annotations)

    annotate_cog(protein_files, in_annotations)
    genome2cdd = parse_annotation(in_annotations, top_hit=True, evalue=evalue)
    write_cog(outdir, genome2cdd, in_proteins, genome_ids=gids, get_type='prot')
    # write_cog(outdir + '_nuc', genome2cdd, in_proteins, genome_ids=gids, get_type='nuc')

    _subgenome2cdd = {k: v for k, v in genome2cdd.items() if k in set(gids)}
    gene_ids = set([_ for vl in genome2cdd.values() for _ in vl])
    gene_multi, gene_Ubiquity, gene2genome_num, gene2genomes = stats_cog(_subgenome2cdd, gene_ids)

    bb_g = [k for k, v in gene2genome_num.items() if v == len(gids)]
    if bb_g and gids:
        print(f"backbone genes is {str(bb_g)}")
    else:
        if genome_list:
            print("No backbone genes... all gene2genomes data could be reviewed at .. ")


if __name__ == "__main__":
    main()
