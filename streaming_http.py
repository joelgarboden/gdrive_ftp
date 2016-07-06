#https://github.com/google/google-api-python-client/blob/68bce4ea78c5cbb4578b8a380886d18b35156a10/googleapiclient/http.py#L886-L971
import copy

from googleapiclient.http import HttpRequest as old_http
from googleapiclient.http import _retry_request, _StreamSlice

class StreamingHttpRequest(old_http):

  def next_chunk(self, http=None, num_retries=0):
    """Execute the next step of a resumable upload.
    Can only be used if the method being executed supports media uploads and
    the MediaUpload object passed in was flagged as using resumable upload.
    Example:
      media = MediaFileUpload('cow.png', mimetype='image/png',
                              chunksize=1000, resumable=True)
      request = farm.animals().insert(
          id='cow',
          name='cow.png',
          media_body=media)
      response = None
      while response is None:
        status, response = request.next_chunk()
        if status:
          print "Upload %d%% complete." % int(status.progress() * 100)
    Args:
      http: httplib2.Http, an http object to be used in place of the
            one the HttpRequest request object was constructed with.
      num_retries: Integer, number of times to retry 500's with randomized
            exponential backoff. If all retries fail, the raised HttpError
            represents the last request. If zero (default), we attempt the
            request only once.
    Returns:
      (status, body): (ResumableMediaStatus, object)
         The body will be None until the resumable media is fully uploaded.
    Raises:
      googleapiclient.errors.HttpError if the response was not a 2xx.
      httplib2.HttpLib2Error if a transport error has occured.
    """
    print("New next_chunk")
    if http is None:
      http = self.http

    if self.resumable.size() is None:
      size = '*'
    else:
      size = str(self.resumable.size())

    print "next_chunk size", size

    if self.resumable_uri is None:
      start_headers = copy.copy(self.headers)
      start_headers['X-Upload-Content-Type'] = self.resumable.mimetype()
      if size != '*':
        print "X-Upload-Content-Length", size
        start_headers['X-Upload-Content-Length'] = size
      start_headers['content-length'] = str(self.body_size)
      print "content-length self.body_size", self.body_size

      resp, content = _retry_request(
          http, num_retries, 'resumable URI request', self._sleep, self._rand,
          self.uri, method=self.method, body=self.body, headers=start_headers)

      if resp.status == 200 and 'location' in resp:
        self.resumable_uri = resp['location']
      else:
        raise ResumableUploadError(resp, content)
    elif self._in_error_state:
      # If we are in an error state then query the server for current state of
      # the upload by sending an empty PUT and reading the 'range' header in
      # the response.
      headers = {
          'Content-Range': 'bytes */%s' % size,
          'content-length': '0'
          }
      resp, content = http.request(self.resumable_uri, 'PUT',
                                   headers=headers)
      status, body = self._process_response(resp, content)
      if body:
        # The upload was complete.
        return (status, body)

    if self.resumable.has_stream():
      data = self.resumable.stream()
      if self.resumable.chunksize() == -1:
        data.seek(self.resumable_progress)
        chunk_end = self.resumable.size() - self.resumable_progress - 1
      else:
        print("Doing chunking with a stream, so wrap a slice of the stream.")
        # Doing chunking with a stream, so wrap a slice of the stream.
        data = _StreamSlice(data, self.resumable_progress,
                            self.resumable.chunksize())
        chunk_end = min(self.resumable_progress + self.resumable.chunksize() - 1,
                        self.resumable.size() - 1)
        print "Chunk end", chunk_end
    else:
      data = self.resumable.getbytes(self.resumable_progress, self.resumable.chunksize())
      print "Not stream"
      # A short read implies that we are at EOF, so finish the upload.
      if len(data) < self.resumable.chunksize():
        size = str(self.resumable_progress + len(data))
        print "Short read", size
      chunk_end = self.resumable_progress + len(data) - 1
      print "Chunk end", chunk_end

    headers = {
        'Content-Range': 'bytes %d-%d/%s' % ( self.resumable_progress, chunk_end, size),
        # Must set the content-length header here because httplib can't
        # calculate the size when working with _StreamSlice.
        'Content-Length': str(chunk_end - self.resumable_progress + 1)
        }
    print "next_chunk headers", headers

    for retry_num in range(num_retries + 1):
      if retry_num > 0:
        self._sleep(self._rand() * 2**retry_num)
        LOGGER.warning(
            'Retry #%d for media upload: %s %s, following status: %d'
            % (retry_num, self.method, self.uri, resp.status))

      try:
        resp, content = http.request(self.resumable_uri, method='PUT',
                                     body=data,
                                     headers=headers)
      except:
        self._in_error_state = True
        raise
      if resp.status < 500:
        break

    return self._process_response(resp, content)
