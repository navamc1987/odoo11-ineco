// Copyright (c) 2010 INECO PARTNERSHIP LIMITED (http://www.ineco.co.th)
// All Right Reserved

odoo.define('ineco_report_client_v11.report', function (require) {
    'use strict';

    var ActionManager = require('web.ActionManager');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');

    ActionManager.include({
        ir_actions_report: function (action, options) {
            var self = this;
            var cloned_action = _.clone(action);
            if (cloned_action.report_type === 'ineco') {
                framework.blockUI();
                var report_ineco_url = '/report/ineco/' + cloned_action.report_name;
                if (cloned_action.context.active_ids) {
                    report_ineco_url += '/' + cloned_action.context.active_ids.join(',');
                } else {
                    report_ineco_url += '?options=' + encodeURIComponent(JSON.stringify(cloned_action.data));
                    report_ineco_url += '&context=' + encodeURIComponent(JSON.stringify(cloned_action.context));
                }
                self.getSession().get_file({
                    url: report_ineco_url,
                    report_file: cloned_action.report_file,
                    data: {
                        data: JSON.stringify([
                            report_ineco_url,
                            cloned_action.report_type
                        ])
                    },
                    error: crash_manager.rpc_error.bind(crash_manager),
                    success: function () {
                        if (cloned_action && options && !cloned_action.dialog) {
                            options.on_close();
                        }
                    }
                });
                framework.unblockUI();
                return;
            }
            return self._super(action, options);
        }
    });
});
