HecTime Class
=============

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec.html#HecTime>`_

General
=======

HecTime objects are unnamed objects that represent instances in time at various granularities that affect the precision
and range of instances supported

.. raw:: html

    <table border="1">
      <thead>
        <tr>
          <th>Granularity</th>
          <th>Precision</th>
          <th>Range</th>
          <th>Time Zone?</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1 Second</td>
          <td>year, month, day, hour, minute, second</td>
          <td>
            <pre>1901-12-13T20:45:52</pre>
            <pre>2038-01-19T03:14:07</pre>
          </td>
          <td>Yes</td>
        </tr>
        <tr>
          <td>1 Minute</td>
          <td>year, month, day, hour, minute</td>
          <td>
            <pre>-2184-12-06T12:52</pre>
            <pre> 5938-01-23T02:07</pre>
          </td>
          <td>Yes</td>
        </tr>
      </tbody>
    </table>
