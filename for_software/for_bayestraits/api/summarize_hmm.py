from tqdm import tqdm
from glob import glob
from collections import defaultdict
import pandas as pd
from dating_workflow.step_script import convert_genome_ID_rev
import click
from os.path import join,exists
import os

def retrieve_info(indir, suffix):
    gid2locus2ko = defaultdict(list)
    files_list = glob(join(indir, f'.{suffix}'))
    if not files_list:
        exit(f"no files could be found with input {join(indir, f'.{suffix}')},please check the parameters. ")
    tqdm.write("reading all annotated result")
    for hf in tqdm(files_list):
        for row in open(hf):
            if row.startswith('#'):
                continue
            r = row.split(' ')
            r = [_ for _ in r if _]
            gene_id = r[0]
            ko = r[2]
            evalue = float(r[4])
            gid2locus2ko[convert_genome_ID_rev(gene_id)].append(
                (gene_id, ko, evalue))
    return gid2locus2ko


def filtration_part(gid2locus2ko, evalue=1e-50):
    # filter out with hard threshold of evalue
    post_filtered = {k: [(_[1], _[0], _[2])
                            for _ in v if _[2] <= evalue]
                        for k, v in tqdm(gid2locus2ko.items())}
    # select minimum evalue among all matched KO for each locus
    # TODO: it may be corrected at following version
    # it could considerate the position overlapping situations
    used_locus = {}
    locus2ko = {}
    tqdm.write("choose best ko for each locus")
    for gid, inlist in tqdm(post_filtered.items()):
        for key, v, evalue in inlist:
            if evalue <= used_locus.get(v, 100):
                used_locus[v] = evalue
                locus2ko[v] = key
    # tqdm.write("choose best ko for each locus")
    post_filtered = defaultdict(lambda: defaultdict(list))
    for locus, ko in locus2ko.items():
        gid = convert_genome_ID_rev(locus)
        post_filtered[gid][ko].append(locus)

    post_filtered = {g: {ko: ','.join(v) for ko, v in d.items()}
                        for g, d in post_filtered.items()}
    return post_filtered



@click.command()
@click.option("-i", "indir", )
@click.option("-o", "odir", )
@click.option("-s", 'suffix')
@click.option("-p", 'prefix',default=None,help='prefix of output file, just the file name, it does not need to include dir name. ')
@click.option("-e", "evalue",default=1e-20)
@click.option("-t", "transpose",default=False,is_flag=True)
def main(indir, odir,suffix, evalue, transpose,prefix):
    gid2locus2ko = retrieve_info(indir, suffix)
    post_filtered = filtration_part(gid2locus2ko,evalue)
    if not exists(odir):
        os.makedirs(odir)

    if prefix is not None:
        ofile_info = join(odir,f"{prefix}_info.tab")
        ofile_binary = join(odir,f"{prefix}_binary.tab")
        ofile_num = join(odir,f"{prefix}_num.tab")
    else:
        ofile_info = join(odir,"merged_hmm_info.tab")
        ofile_binary = join(odir,"merged_hmm_binary.tab")
        ofile_num = join(odir,"merged_hmm_num.tab")

    final_df = pd.DataFrame.from_dict(post_filtered, orient='index')
    bin_df = final_df.applymap(lambda x: 1 if pd.isna(x) else 0)
    num_df = final_df.applymap(lambda x: len(x.split(',')) if pd.isna(x) else 0)
    if transpose:
        final_df = final_df.T
        bin_df = bin_df.T
        num_df = num_df.T
    final_df.to_csv(ofile_info,sep='\t',index=1)
    bin_df.to_csv(ofile_binary,sep='\t',index=1)
    num_df.to_csv(ofile_num,sep='\t',index=1)

    
if __name__ == "__main__":
    main()
