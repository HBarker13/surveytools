SurveyTools
===========
A Python library used to create data products for the VPHAS+ photometric
survey of the Galactic Plane.

Example use
-----------
Creating a pretty plot showing the 32-CCD mosaic of a VST/OmegaCAM FITS file:
```
mosaicplot -o prettyplot.jpg omegacam_exposure.fits
```

Creating a multi-band catalogue of PSF photometry for a VPHAS pointing:
```Python
import surveytools
pointing = surveytools.VphasPointing('0149a')
pointing.create_catalogue().write('mycatalogue.fits')
```

Dependencies
------------
* `astropy` v1.0
* `astropy-photutils` v0.1
* `pyraf` (requires a local installation of IRAF)
* `progressbar`