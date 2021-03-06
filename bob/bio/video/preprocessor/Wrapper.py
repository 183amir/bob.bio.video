import bob.bio.base
import numpy
import glob
import os

import bob.io.base

from .. import utils

class Wrapper (bob.bio.base.preprocessor.Preprocessor):
  """Wrapper class to run image preprocessing algorithms on video data.

  This class provides functionality to read original video data from several databases.
  So far, the video content from :py:class:`bob.db.mobio` and the image list content from :py:class:`bob.db.youtube` are supported.

  Furthermore, frames are extracted from these video data, and a ``preprocessor`` algorithm is applied on all selected frames.
  The preprocessor can either be provided as a registered resource, i.e., one of :ref:`bob.bio.face.preprocessors`, or an instance of a preprocessing class.
  Since most of the databases do not provide annotations for all frames of the videos, commonly the preprocessor needs to apply face detection.

  The ``frame_selector`` can be chosen to select some frames from the video.
  By default, a few frames spread over the whole video sequence are selected.

  The ``quality_function`` is used to assess the quality of the frame.
  If no ``quality_function`` is given, the quality is based on the face detector, or simply left as ``None``.
  So far, the quality of the frames are not used, but it is foreseen to select frames based on quality.

  **Parameters:**

  preprocessor : str or :py:class:`bob.bio.base.preprocessor.Preprocessor` instance
    The preprocessor to be used to preprocess the frames.

  frame_selector : :py:class:`bob.bio.video.FrameSelector`
    A frame selector class to define, which frames of the video to use.

  quality_function : function or ``None``
    A function assessing the quality of the preprocessed image.
    If ``None``, no quality assessment is performed.
    If the preprocessor contains a ``quality`` attribute, this is taken instead.

  compressed_io : bool
    Use compression to write the resulting preprocessed HDF5 files.
    This is experimental and might cause trouble.
    Use this flag with care.
  """

  def __init__(self,
      preprocessor = 'landmark-detect',
      frame_selector = utils.FrameSelector(),
      quality_function = None,
      compressed_io = False
  ):

    # load preprocessor configuration
    if isinstance(preprocessor, str):
      self.preprocessor = bob.bio.base.load_resource(preprocessor, "preprocessor")
    elif isinstance(preprocessor, bob.bio.base.preprocessor.Preprocessor):
      self.preprocessor = preprocessor
    else:
      raise ValueError("The given algorithm could not be interpreter")

    bob.bio.base.preprocessor.Preprocessor.__init__(
        self,
        preprocessor=preprocessor,
        frame_selector=frame_selector,
        compressed_io=compressed_io
    )

    self.frame_selector = frame_selector
    self.quality_function = quality_function
    self.compressed_io = compressed_io

  def _check_data(self, frames):
    """Checks if the given video is in the desired format."""
    assert isinstance(frames, utils.FrameContainer)


  def __call__(self, frames, annotations = None):
    """__call__(frames, annotations = None) -> preprocessed

    Preprocesses the given frames using the desired ``preprocessor``.

    Faces are extracted for all frames in the given frame container, using the ``preprocessor`` specified in the constructor.

    If given, the annotations need to be in a dictionary.
    The key is either the frame number (for video data) or the image name (for image list data).
    The value is another dictionary, building the relation between facial landmark names and their location, e.g. ``{'leye' : (le_y, le_x), 'reye' : (re_y, re_x)}``

    The annotations for the according frames, if present, are passed to the preprocessor.
    Please assure that your database interface provides the annotations in the desired format.

    **Parameters:**

    frames : :py:class:`bob.bio.video.FrameContainer`
      The pre-selected frames, as returned by :py:meth:`read_original_data`.

    annotations : dict or ``None``
      The annotations for the frames, if any.

    **Returns:**

    preprocessed : :py:class:`bob.bio.video.FrameContainer`
      A frame container that contains the preprocessed frames.
    """

    self._check_data(frames)

    annots = None
    fc = utils.FrameContainer()

    for index, frame, _ in frames:
      # if annotations are given, we take them
      if annotations is not None: annots = annotations[index]

      # preprocess image (by default: detect a face)
      preprocessed = self.preprocessor(frame, annots)
      if preprocessed is not None:
        # compute the quality of the detection
        if self.quality_function is not None:
          quality = self.quality_function(preprocessed)
        elif hasattr(self.preprocessor, 'quality'):
          quality = self.preprocessor.quality
        else:
          quality = None
        # add image to frame container
        fc.add(index, preprocessed, quality)

    return fc


  def read_original_data(self, data):
    """read_original_data(data) -> frames

    Reads the original data from file and selects some frames using the desired ``frame_selector``.

    Currently, two types of data is supported:

    1. video data, which is stored in a 3D or 4D :py:class:`numpy.ndarray`, which will be read using :py:func:`bob.io.base.load`
    2. image lists, which is given as a list of strings of image file names. Each image will be read with :py:func:`bob.io.base.load`

    **Parameters:**

    data : 3d or 4D :py:class:`numpy.ndarray`, or [str]
      The original data to read.

    **Returns:**

    frames : :py:class:`bob.bio.video.FrameContainer`
      The selected frames, stored in a frame container.
    """
    return self.frame_selector(data)


  def read_data(self, filename):
    """read_data(filename) -> frames

    Reads the preprocessed data from file and returns them in a frame container.
    The preprocessors ``read_data`` function is used to read the data for each frame.

    **Parameters:**

    filename : str
      The name of the preprocessed data file.

    **Returns:**

    frames : :py:class:`bob.bio.video.FrameContainer`
      The read frames, stored in a frame container.
    """
    if self.compressed_io:
      return utils.load_compressed(filename, self.preprocessor.read_data)
    else:
      return utils.FrameContainer(bob.io.base.HDF5File(filename), self.preprocessor.read_data)


  def write_data(self, frames, filename):
    """Writes the preprocessed data to file.

    The preprocessors ``write_data`` function is used to write the data for each frame.

    **Parameters:**

    frames : :py:class:`bob.bio.video.FrameContainer`
      The preprocessed frames, as returned by the :py:meth:`__call__` function.

    filename : str
      The name of the preprocessed data file to write.
    """
    self._check_data(frames)

    if self.compressed_io:
      return utils.save_compressed(frames, filename, self.preprocessor.write_data)
    else:
      frames.save(bob.io.base.HDF5File(filename, 'w'), self.preprocessor.write_data)
