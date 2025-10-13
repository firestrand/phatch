gui
***

The main wxPython entry point for Phatch now delegates most responsibilities
to explicit helper classes. `FrameDependencies` wires together the services,
`DialogService` encapsulates dialog/notification flows, and
`FileMenuCoordinator` manages file-menu workflows. Both the main desktop app
and droplet launcher reuse the same dependency bundle, allowing tests to
inject fakes without touching wx.

.. automodule:: pyWx.gui
   :members:
   :undoc-members:
   :show-inheritance:
