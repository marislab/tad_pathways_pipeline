"""
2016 Gregory Way
TAD Pathways
scripts/build_custom_tad_genelist.py

Description:
build genelists of all genes in TADs harboring significant SNPs

Usage:
Run on the command line:

    python scripts/build_custom_tad_genelist.py

With the following required flags:

    --snp_data_file     The file name of where SNP data is stored. SNP data is
                        generated by `scripts/build_snp_list.R`
    --output_file       The name of the results file to build
    --TAD_Boundary      The name of tad cell to use

Output:
Trait specific .tsv files of one column each indicating all the genes that fall
in signal TADs
"""

import os
import argparse
import pandas as pd

# Load Command Arguments
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--snp_data_file", help="Location of SNP data")
parser.add_argument("-o", "--output_file", help="Name of the output file")
parser.add_argument("-t", "--TAD_Boundary", help="Name of the tad cell")
args = parser.parse_args()


def assign_custom_snp_to_tad(snp_signal, tad_boundary):
    """
    Take an input snp signal and TAD boundary coordinates to output the
    coordinates of TAD where the SNP signal resides.

    Arguments:
    :param snp_signal: Pandas Series with SNP descriptive attributes
    :param tad_boundary: a Pandas DataFrame of all TADs and genomic locations

    Output:
    an OrderedDict object storing SNP and TAD specific info
    """
    chrom = ('chrom', str(snp_signal.chrom[3:]))
    snp_loc = ('snploc', int(snp_signal.position))

    tad = tad_boundary.ix[
        (tad_boundary.chromosome == str(chrom[1])) &
        (tad_boundary.TAD_start <= snp_loc[1]) &
        (tad_boundary.TAD_end > snp_loc[1])
    ]

    return tad.reset_index(drop=True)

# Load Constants
snp_data_file = args.snp_data_file
output_file = args.output_file
output_nearest_gene_file = '{}_nearest_gene.tsv'.format(
    os.path.splitext(output_file)[0])

# Load data
index_file = "GENE_index_hg19_" + tad_cell + ".tsv.bz2"
tad_genes_df = pd.read_table(os.path.join('data',index_file),
                             index_col=0)
# The SNP DataFrame has the columns [RSid, database source, chromosome,
# genomic position, minor allele, and group]
snp_df = pd.read_table(snp_data_file)

# Initialize empty DataFrames that will store all TAD results and nearest genes
# "group" is specified by the input file to "scripts/tad_util/build_snp_list.R"
# We allow mulitple group queries to build separate TAD based genelists.
results_df = pd.DataFrame(columns=tad_genes_df.columns.tolist() + ['group'])
nearest_gene_df = pd.DataFrame(columns=['gene', 'snp', 'group'])
for group in snp_df.group.unique():
    snp_sub_df = snp_df[snp_df['group'] == group]
    # Loop over each group specific SNP
    for snp, snp_series in snp_sub_df.iterrows():
        # Find TAD that the SNP resides in and all genes that are in the TAD
        tad_assignment = assign_custom_snp_to_tad(snp_series, tad_genes_df)

        # Only collect genes if the SNP actually resides in a TAD
        if tad_assignment.shape[0] != 0:

            # Subset to protein coding genes for nearest gene designation
            protein_coding = tad_assignment[tad_assignment['gene_type'] ==
                                            'protein_coding']
            # Find nearest gene
            # Closest to the start of the gene
            dist_df = pd.DataFrame((protein_coding.start -
                                    snp_series['position']).abs()
                                                           .sort_values())
            # Closest to the end of a the gene
            dist_df = dist_df.join(
                        pd.DataFrame((protein_coding.stop -
                                      snp_series['position']).abs()
                                                             .sort_values()))
            # Find the minimum distance and the index of a protein coding gene
            near_gene_idx = dist_df[dist_df ==
                                    dist_df.min().min()].dropna(thresh=1).index

            # If gene falls in TAD without protein coding gene return empty
            if len(near_gene_idx) == 0:
                nearest_gene = ''
            else:
                near_gene_idx = near_gene_idx.tolist()[0]
                nearest_gene = tad_assignment.ix[near_gene_idx].gene_name

            # Append to nearest_gene_df
            nearest_gene_return = pd.DataFrame([nearest_gene,
                                                snp_series.snp, group]).T
            nearest_gene_return.columns = ['gene', 'snp', 'group']
            nearest_gene_df = nearest_gene_df.append(nearest_gene_return,
                                                     ignore_index=True)

            # Assign new columns to each TAD assignment for the RSid and group
            tad_assignment = tad_assignment.assign(custom_snp=snp_series.snp)
            tad_assignment = tad_assignment.assign(group=group)
            results_df = results_df.append(tad_assignment, ignore_index=True)

# Output results
nearest_gene_df.columns = ['MAPPED_GENE', 'snp', 'group']
results_df.columns = ['TADEnd', 'TADidx', 'TADStart', 'chrom', 'custom_snp',
                      'db', 'gene_name', 'gene_type', 'group', 'start', 'stop',
                      'strand', 'type']
results_df.to_csv(output_file, sep='\t', index=False)
nearest_gene_df.to_csv(output_nearest_gene_file, sep='\t')
