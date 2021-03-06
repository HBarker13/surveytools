"""Applies the APASS-based calibration to the resolved catalogues."""
import os
import glob

import numpy as np

from astropy import log
from astropy import table
from astropy.table import Table
from astropy.io import fits

from surveytools import SURVEYTOOLS_DATA

def get_calib_group(imagetbl="vphas-dr2-red-images.fits"):
    tbl = table.Table.read(os.path.join(SURVEYTOOLS_DATA, imagetbl))
    tbl['night'] = [fn[0:9] for fn in tbl['image file']]
    calib_groups = {}
    for group in tbl.group_by('night').groups:
        fields = np.unique(group['Field_1'])
        mygroup = [fld.split('_')[1]+off for fld in fields for off in ['a', 'b']]
        for offset in mygroup:
            calib_groups[offset] = mygroup
    return calib_groups

RED_GROUPS = get_calib_group("vphas-dr2-red-images.fits")
BLUE_GROUPS = get_calib_group("vphas-dr2-blue-images.fits")


# Read the per-offset shifts into a dictionary
SHIFTS_TBL = Table.read('shifts-mike.fits')
SHIFTS = dict(zip(SHIFTS_TBL['field'], SHIFTS_TBL))

INDEX_TBL = Table.read('/car-data/gb/vphas/psfcat/vphas-offsetcats.fits')
HA_ZPT_CORR = dict(zip(INDEX_TBL['offset'], -(3.01 - (INDEX_TBL['rzpt'] - INDEX_TBL['hazpt']))))

# From Fukugita (1996)
VEGA2AB = {'u': 0.961, 'g': -0.123, 'r2': 0.136, 'r': 0.136, 'i': 0.373}

def get_median_shifts():
    """Returns the median shifts, to be used in the case of insufficient APASS calibrators."""
    shifts = {}
    for band in ['u', 'g', 'r2', 'r', 'i']:
        shifts[band] = np.nanmedian(SHIFTS_TBL[band + 'shift'])
        shifts[band + '_ab'] = shifts[band] + VEGA2AB[band]
    # H-alpha uses the r-band shift but requires a special ZPT correction to fix the offset to 3.01
    shifts['ha'] = shifts['r'] + np.median([x for x in HA_ZPT_CORR.values()])
    return shifts


def get_night_shifts(offset):
    """Returns the mean APASS-based shifts for all the offsets in the same night."""
    shifts = {}
    shifts_std = {}
    for band in ['r', 'i']:
        offset_shifts = []
        for sibling in red_groups[offset]:
            try:
                offset_shifts.append(SHIFTS[sibling][band + 'shift'])
            except KeyError:
                pass
        shifts[band] = np.nanmean(offset_shifts)
        shifts_std[band] = np.nanstd(offset_shifts)
    if offset not in blue_groups:
        for band in ['u', 'g', 'r2']:
            shifts[band] = np.nan
    else:
        for band in ['u', 'g', 'r2']:
            offset_shifts = []
            for sibling in blue_groups[offset]:
                try:
                    offset_shifts.append(SHIFTS[sibling][band + 'shift'])
                except KeyError:
                    pass
            shifts[band] = np.nanmean(offset_shifts)
            shifts_std[band] = np.nanstd(offset_shifts)
    return shifts, shifts_std


def get_shifts(offset):
    """Returns the shifts to apply to the various columns."""
    #if offset not in SHIFTS:
    #    log.warning('Using median offsets for {}'.format(offset))
    #    return get_median_shifts()
    #shifts = {}
    #for band in ['u', 'g', 'r2', 'r', 'i']:
    #    shifts[band] = SHIFTS[offset][band + 'shift']
    #    if np.isnan(shifts[band]):
    #        shifts[band] = get_median_shifts()[band]
    shifts, shifts_std = get_night_shifts(offset)
    for band in shifts.keys():
        shifts[band + '_ab'] = shifts[band] + VEGA2AB[band]
    # H-alpha uses the r-band shift but requires a special ZPT correction to fix the offset to 3.01
    hazpcorr = HA_ZPT_CORR[offset]
    log.debug('Ha zeropoint correction: {:+.2f}'.format(hazpcorr))
    shifts['ha'] = shifts['r'] + hazpcorr
    return shifts


def apply_calibration(input_fn):
    offset = input_fn.split('/')[-1].split('-')[0]
    shifts = get_shifts(offset)
    #log.info(shifts)

    log.info('Opening {}'.format(input_fn))
    cat = fits.open(input_fn, memmap=False)
    for band in ['u', 'g', 'r2', 'ha', 'r', 'i']:
        cat[1].data[band] += shifts[band]
        cat[1].data['aperMag_' + band] += shifts[band]
        cat[1].data['magLim_' + band] += shifts[band]
        if band != 'ha':
            cat[1].data[band + '_ab'] += shifts[band + '_ab']
            cat[1].data['aperMag_' + band + '_ab'] += shifts[band + '_ab']

    # Also correct the colours
    cat[1].data['u_g'] += shifts['u'] - shifts['g']
    cat[1].data['g_r2'] += shifts['g'] - shifts['r2']
    cat[1].data['r_i'] += shifts['r'] - shifts['i']
    cat[1].data['r_ha'] += shifts['r'] - shifts['ha']

    output_fn = input_fn.replace('resolved.fits', 'calibrated.fits')
    log.info('Writing {}'.format(output_fn))
    cat.writeto(output_fn, clobber=True)
    

if __name__ == '__main__':
    log.setLevel('INFO')
    filenames = glob.glob('/car-data/gb/vphas/psfcat/resolved/*resolved.fits')

    import multiprocessing
    pool = multiprocessing.Pool(16)
    pool.map(apply_calibration, filenames)
    #apply_calibration('tmp/0005a-1-resolved.fits')
