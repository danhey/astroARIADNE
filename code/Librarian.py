"""Helper class to look up broadband photometry and stellar parameters."""
import warnings

import astropy.units as u
import scipy as sp
from astropy.coordinates import Angle, SkyCoord
from astropy.utils.exceptions import AstropyWarning
from astroquery.gaia import Gaia
from astroquery.vizier import Vizier
from tqdm import tqdm

from Error import CatalogWarning

warnings.filterwarnings('ignore', category=UserWarning, append=True)
warnings.filterwarnings('ignore', category=AstropyWarning, append=True)
Vizier.ROW_LIMIT = -1
Vizier.columns = ['all']


class Librarian:
    """Docstring."""

    # pyphot filter names: currently unused are U R I PS1_w

    filter_names = sp.array([
        '2MASS_H', '2MASS_J', '2MASS_Ks',
        'GROUND_JOHNSON_U', 'GROUND_JOHNSON_V', 'GROUND_JOHNSON_B',
        'GaiaDR2v2_G', 'GaiaDR2v2_RP', 'GaiaDR2v2_BP',
        'PS1_g', 'PS1_i', 'PS1_r', 'PS1_w', 'PS1_y',  'PS1_z',
        'SDSS_g', 'SDSS_i', 'SDSS_r', 'SDSS_u', 'SDSS_z',
        'WISE_RSR_W1', 'WISE_RSR_W2', 'GALEX_FUV', 'GALEX_NUV'
    ])

    # Catalogs magnitude names
    # NOTE: SDSS_z is breaking the fit for some reason.
    __apass_mags = ['Vmag', 'Bmag', 'g_mag', 'r_mag', 'i_mag']
    __apass_errs = ['e_Vmag', 'e_Bmag', 'e_g_mag', 'e_r_mag', 'e_i_mag']
    __apass_filters = ['GROUND_JOHNSON_V', 'GROUND_JOHNSON_B',
                       'SDSS_g', 'SDSS_r', 'SDSS_i']
    __ascc_mags = ['Vmag', 'Bmag', 'Jmag', 'Hmag', 'Kmag']
    __ascc_errs = ['e_Vmag', 'e_Bmag', 'e_Jmag', 'e_Hmag', 'e_Kmag']
    __ascc_filters = ['GROUND_JOHNSON_V', 'GROUND_JOHNSON_B',
                      '2MASS_J', '2MASS_H', '2MASS_Ks']
    __wise_mags = ['W1mag', 'W2mag']
    __wise_errs = ['e_W1mag', 'e_W2mag']
    __wise_filters = ['WISE_RSR_W1', 'WISE_RSR_W2']
    __ps1_mags = ['gmag', 'rmag', 'imag', 'zmag', 'ymag']
    __ps1_errs = ['e_gmag', 'e_rmag', 'e_imag', 'e_zmag', 'e_ymag']
    __ps1_filters = ['PS1_g', 'PS1_r', 'PS1_i', 'PS1_z', 'PS1_y']
    __twomass_mags = ['Jmag', 'Hmag', 'Kmag']
    __twomass_errs = ['e_Jmag', 'e_Hmag', 'e_Kmag']
    __twomass_filters = ['2MASS_J', '2MASS_H', '2MASS_Ks']
    __gaia_mags = ['Gmag', 'BPmag', 'RPmag']
    __gaia_errs = ['e_Gmag', 'e_BPmag', 'e_RPmag']
    __gaia_filters = ['GaiaDR2v2_G',  'GaiaDR2v2_BP', 'GaiaDR2v2_RP']
    # __sdss_mags = ['umag']
    __sdss_mags = ['umag', 'gmag', 'rmag', 'imag', 'zmag']
    # __sdss_errs = ['e_umag']
    __sdss_errs = ['e_umag', 'e_gmag', 'e_rmag', 'e_imag', 'e_zmag']
    # __sdss_filters = ['SDSS_u']
    __sdss_filters = ['SDSS_u', 'SDSS_g', 'SDSS_r', 'SDSS_i', 'SDSS_z']
    __galex_mags = ['FUV', 'NUV']
    __galex_errs = ['e_FUV', 'e_NUV']
    __galex_filters = ['GALEX_FUV', 'GALEX_NUV']

    # APASS DR9, WISE, PAN-STARRS DR1, GAIA DR2, 2MASS, SDSS DR9
    catalogs = {
        'ASCC': [
            'I/280B/ascc',
            zip(__ascc_mags, __ascc_errs, __ascc_filters)
        ],
        'APASS': [
            'II/336/apass9',
            zip(__apass_mags, __apass_errs, __apass_filters)
        ],
        'Wise': [
            'II/328/allwise',
            zip(__wise_mags, __wise_errs, __wise_filters)
        ],
        'Pan-STARRS':
        [
            'II/349/ps1',
            zip(__ps1_mags, __ps1_errs, __ps1_filters)
        ],
        'Gaia':
        [
            'I/345/gaia2',
            zip(__gaia_mags, __gaia_errs, __gaia_filters)
        ],
        '2MASS': [
            'II/246/out',
            zip(__twomass_mags, __twomass_errs, __twomass_filters)
        ],
        'SDSS': [
            'V/147/sdss12', zip(__sdss_mags, __sdss_errs, __sdss_filters)
        ],
        'GALEX': [
            'II/312/ais', zip(__galex_mags, __galex_errs, __galex_filters)
        ]
    }

    def __init__(self, starname, ra, dec, radius=None, g_id=None,
                 verbose=True, mags=True):
        self.starname = starname
        self.ra = ra
        self.dec = dec
        self.verbose = verbose

        self.used_filters = sp.zeros(self.filter_names.shape[0])
        self.mags = sp.zeros(self.filter_names.shape[0])
        self.mag_errs = sp.zeros(self.filter_names.shape[0])

        if radius is None:
            self.radius = 20 * u.arcsec
        else:
            self.radius = radius
        if g_id is None:
            if verbose:
                print('No Gaia ID provided. Searching for nearest source.')
            self.g_id = self._get_gaia_id()
            if verbose:
                print('Gaia ID found: {0}'.format(self.g_id))
        else:
            self.g_id = g_id

        self.gaia_params()
        if mags:
            self.gaia_query()

        pass

    def gaia_params(self):
        """Retrieve parallax, radius, teff and lum from Gaia."""
        # If gaia DR2 id is provided, query by id
        fields = sp.array([
            'parallax', 'parallax_error', 'teff_val',
            'teff_percentile_lower', 'teff_percentile_upper',
            'radius_val', 'radius_percentile_lower',
            'radius_percentile_upper', 'lum_val',
            'lum_percentile_lower', 'lum_percentile_upper'
        ])
        query = 'select '
        for f in fields[:-1]:
            query += 'gaia.' + f + ', '
        query += 'gaia.' + fields[-1]
        query += ' from gaiadr2.gaia_source as gaia'
        query += ' where gaia.source_id={0}'.format(self.g_id)
        j = Gaia.launch_job_async(query)
        res = j.get_results()
        self.plx, self.plx_e = self._get_parallax(res)
        self.temp, self.temp_e = self._get_teff(res)
        self.rad, self.rad_e = self._get_radius(res)
        self.lum, self.lum_e = self._get_lum(res)
        pass

    def _get_parallax(self, res):
        plx = res['parallax'][0]
        if plx <= 0:
            CatalogWarning(0, 0).warn()
            return 0, 0
        plx_e = res['parallax_error'][0]
        # Parallax correction.
        return plx + 0.082, sp.sqrt(plx_e ** 2 + 0.033**2)

    def _get_radius(self, res):
        rad = res['radius_val'][0]
        if sp.ma.is_masked(rad):
            CatalogWarning('radius', 1).warn()
            return 0, 0
        lo = res['radius_percentile_lower'][0]
        up = res['radius_percentile_upper'][0]
        rad_e = max([rad - lo, up - rad])
        return rad, rad_e

    def _get_teff(self, res):
        teff = res['teff_val'][0]
        if sp.ma.is_masked(teff):
            CatalogWarning('teff', 1).warn()
            return 0, 0
        lo = res['teff_percentile_lower'][0]
        up = res['teff_percentile_upper'][0]
        teff_e = max([teff - lo, up - teff])
        return teff, teff_e

    def _get_lum(self, res):
        lum = res['lum_val'][0]
        if sp.ma.is_masked(lum):
            CatalogWarning('lum', 1).warn()
            return 0, 0
        lo = res['lum_percentile_lower'][0]
        up = res['lum_percentile_upper'][0]
        lum_e = max([lum - lo, up - lum])
        return lum, lum_e

    def _get_gaia_id(self):
        c = SkyCoord(self.ra, self.dec, unit=(u.deg, u.deg), frame='icrs')
        j = Gaia.cone_search_async(c, self.radius)
        res = j.get_results()
        return res['source_id'][0]

    def gaia_query(self):
        """Query Gaia to get different catalog IDs."""
        # cats = ['tmass', 'panstarrs1', 'sdssdr9', 'allwise']
        # names = ['tmass', 'ps', 'sdss', 'allwise']
        cats = ['tycho2', 'panstarrs1', 'sdssdr9',
                'allwise', 'tmass', 'apassdr9']
        names = ['tycho', 'ps', 'sdss', 'allwise', 'tmass', 'apass']
        IDS = {
            'ASCC': '',  # ASCC uses Tycho-2 id
            'APASS': '',
            '2MASS': '',
            'Pan-STARRS': '',
            'SDSS': '',
            'Wise': '',
            'Gaia': self.g_id
        }
        for c, n in zip(cats, names):
            if c == 'apassdr9':
                cat = 'APASS'
            if c == 'tmass':
                cat = '2MASS'
            if c == 'tycho2':
                cat = 'ASCC'
            if c == 'panstarrs1':
                cat = 'Pan-STARRS'
            if c == 'sdssdr9':
                cat = 'SDSS'
            if c == 'allwise':
                cat = 'Wise'
            query = 'select original_ext_source_id from '
            query += 'gaiadr2.gaia_source as gaia join '
            query += 'gaiadr2.{}_best_neighbour as {} '.format(c, n)
            query += 'on gaia.source_id={}.source_id where '.format(n)
            query += 'gaia.source_id={}'.format(self.g_id)
            j = Gaia.launch_job_async(query)
            r = j.get_results()
            if len(r):
                IDS[cat] = r[0][0]
            else:
                IDS[cat] = 'skipped'
                if self.verbose:
                    CatalogWarning(cat, 5).warn()

        self.ids = IDS

    def get_catalogs(self):
        """Retrieve available catalogs for a star from Vizier."""
        cats = Vizier.query_region(
            SkyCoord(
                ra=self.ra, dec=self.dec, unit=(u.deg, u.deg), frame='icrs'
            ), radius=self.radius
        )

        return cats

    def get_magnitudes(self):
        """Retrieve the magnitudes of the star.

        Looks into APASS, WISE, Pan-STARRS, Gaia, 2MASS and SDSS surveys
        looking for different magnitudes for the star, along with the
        associated uncertainties.
        """
        coord = SkyCoord(self.ra, self.dec, unit=(u.deg, u.deg), frame='icrs')
        if self.verbose:
            print('Looking online for archival magnitudes for star', end=' ')
            print(self.starname)

        cats = self.get_catalogs()

        for c in self.catalogs.keys():
            # load magnitude names, filter names and error names of
            # current catalog
            current = self.catalogs[c][1]
            if c in self.ids.keys():
                if self.ids[c] == 'skipped':
                    continue
                try:
                    current_cat = cats[self.catalogs[c][0]]
                except TypeError:
                    CatalogWarning(c, 5).warn()
                    continue
                if c == 'APASS':
                    self._get_apass(current_cat)
                    continue
                if c == 'Wise':
                    self._get_wise(current_cat)
                    continue
                if c == 'ASCC':
                    self._get_ascc(current_cat)
                    continue
                if c == 'SDSS':
                    self._get_sdss(current_cat)
                    continue
                if c == 'Pan-STARRS':
                    self._get_ps1(current_cat)
                    continue
                if c == 'Gaia':
                    self._get_gaia(current_cat)
                    continue
            else:
                try:
                    # load current catalog
                    current_cat = cats[self.catalogs[c][0]]
                    self._retrieve_from_cat(current_cat)
                except Exception as e:
                    if self.verbose:
                        CatalogWarning(c, 5).warn()
        pass

    def _retrieve_from_cat(self, cat, name):
        for m, e, f in self.catalogs[name][1]:
            filt_idx = sp.where(f == self.filter_names)[0]

            if self.used_filters[filt_idx] == 1:
                if self.verbose:
                    CatalogWarning(f, 6)
                return
            mag = cat[m]
            err = cat[e]
            if sp.ma.is_masked(mag):
                CatalogWarning(m, 2).warn()
                return
            if sp.ma.is_masked(err):
                CatalogWarning(m, 3).warn()
                return
            if err == 0:
                CatalogWarning(m, 4).warn()
                return

            self._add_mags(mag, err, f)

    def _add_mags(self, mag, er, filt):
        filt_idx = sp.where(filt == self.filter_names)[0]
        if self.used_filters[filt_idx] == 1:
            if self.verbose:
                CatalogWarning(filt, 6)
            return
        self.used_filters[filt_idx] = 1
        self.mags[filt_idx] = mag
        self.mag_errs[filt_idx] = er

    def _get_ascc(self, cat):
        tyc1, tyc2, tyc3 = self.ids['ASCC'].split(b'-')
        mask = cat['TYC1'] == tyc1
        mask *= cat['TYC2'] == tyc2
        mask *= cat['TYC3'] == tyc3
        self._retrieve_from_cat(cat[mask], 'ASCC')

    def _get_apass(self, cat):
        mask = cat['recno'] == self.ids['APASS']
        self._retrieve_from_cat(cat[mask], 'APASS')

    def _get_wise(self, cat):
        mask = cat['AllWISE'] == self.ids['Wise']
        self._retrieve_from_cat(cat[mask], 'Wise')

    def _get_2mass(self, cat):
        mask = cat['_2MASS'] == self.ids['2MASS']
        self._retrieve_from_cat(cat[mask], '2MASS')

    def _get_sdss(self, cat):
        mask = cat['SDSS12'] == self.ids['SDSS']
        self._retrieve_from_cat(cat[mask], 'SDSS')

    def _get_ps1(self, cat):
        mask = cat['objID'] == self.ids['Pan-STARRS']
        self._retrieve_from_cat(cat[mask], 'Pan-STARRS')

    def _get_gaia(self, cat):
        mask = cat['DR2Name'] == 'Gaia DR2 {0}'.format(self.ids['Gaia'])
        self._retrieve_from_cat(cat[mask], 'Gaia')
