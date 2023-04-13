/*
 * View model for OctoPrint-ResumePrint
 *
 * Author: Pavulon87
 * License: AGPLv3
 */
$(function () {
  function ResumeprintViewModel(parameters) {
    var self = this;

    console.warn("ResumePrintViewModel", parameters);

    self.loginState = parameters[0];
    self.settingsViewModel = parameters[1];
    self.filesViewModel = parameters[2];
    self.access = parameters[3];
    self.PrinterStateViewModel = parameters[4];

    self.PrinterStateViewModel.resumeLastPrint = function () {
      self.resumeLastPrint();
    };

    // TODO: Implement your plugin's view model here.

    $(document).ready(function () {
      let template2 =
        '<div class="btn btn-mini" data-bind="click: function() { if ($root.loginState.isUser()) { $root.translateSelect($data) } else { return; } }, css: {disabled: !$root.loginState.isUser()}" href="#translate-model-modal" data-toggle="modal" title="Reprint Last File"><i class="fa fa-arrows-alt"></i></div>';

      // let template = '<div class="btn btn-primary" style="width: 100%; margin-top: 10px;" data-bind="click: function() { if ($root.loginState.isUser()) { $root.resumeLastPrint() } else { return; } }, css: {disabled: !$root.loginState.isUser()}" href="#resume-last-print" data-toggle="modal" title="Resume Last Print"><i class="fa fa-print"></i> Resume Last Print</div>';
      let template =
        '<button class="btn btn-primary" data-bind="click: function() { if ($root.loginState.isUser()) { $root.resumeLastPrint() } else { return; } }, disable: enableCancel, attr: {title: \'Resume Last Print\'}" id="resume_last_print" title="Resume Last Print" style="width: 100%; margin-top: 10px;"><i class="fas fa-print" ></i><span> Resume Last Print</span></button>';

      var lastJobButton = $("#job_print").parent().children().last();
      lastJobButton.after(template);
    });

    self.resumeLastPrint = function () {
      $.ajax({
        url: API_BASEURL + "plugin/resumeprint",
        type: "POST",
        dataType: "json",
        data: JSON.stringify({
          command: "resumeprint",
        }),
        contentType: "application/json; charset=UTF-8",
        error: function error(jqXHR, textStatus) {
          new PNotify({
            title: "Resuming failed",
            text: jqXHR.responseText,
            type: "error",
            hide: true,
          });
        },
        success: function success(data) {
          new PNotify({
            title: "Resuming...",
            text: data.msg,
            type: "info",
            hide: true,
          });
          console.info(data);
        },
      });
    };
  }

  /* view model class, parameters for constructor, container to bind to
   * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
   * and a full list of the available options.
   */
  OCTOPRINT_VIEWMODELS.push({
    construct: ResumeprintViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...

    dependencies: [
      "loginStateViewModel",
      "settingsViewModel",
      "filesViewModel",
      "accessViewModel",
      "printerStateViewModel",
    ],
    // Elements to bind to, e.g. #settings_plugin_resumeprint, #tab_plugin_resumeprint, ...
    elements: ["#settings_plugin_resumeprint"],
  });
});
