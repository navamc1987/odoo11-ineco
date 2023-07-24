odoo.define('ineco.help', function (require) {
    "use strict";

    var config = require('web.config');
    var core = require('web.core');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var QWeb = core.qweb;

    var YoutubeView = Widget.extend({
        template: "ineco.youtube",
        events: {},
        init: function (parent, url) {
            this._super(parent);
            this.url = url;
        },
        start: function () {
            return this._super();
        },
    })

    var ActivityMenu = Widget.extend({
            template: 'ineco.help.ActivityMenu',
            events: {
                "click": "_onActivityMenuClick",
            },
            start: function () {
                return this._super();
            },
            _getUrlVars: function () {
                var vars = [], hash;
                var hashes = window.location.href.slice(window.location.href.indexOf('#') + 1).split('&');
                for (var i = 0; i < hashes.length; i++) {
                    hash = hashes[i].split('=');
                    vars.push(hash[0]);
                    vars[hash[0]] = hash[1];
                }
                return vars;
            },
            _getActivityData: function () {
                var self = this;
                return self._rpc({
                    model: 'res.users',
                    method: 'activity_user_count',
                    kwargs: {
                        context: session.user_context,
                    },
                }).then(function (data) {
                    self.activities = data;
                    self.activityCounter = _.reduce(data, function (total_count, p_data) {
                        return total_count + p_data.total_count;
                    }, 0);
                    self.$('.o_notification_counter').text(self.activityCounter);
                    self.$el.toggleClass('o_no_notification', !self.activityCounter);
                });
            }
            ,
            _isOpen: function () {
                return this.$el.hasClass('open');
            }
            ,
            _updateActivityPreview: function () {
                var self = this;
                session.rpc('/help/version', {}).done(function (version) {
                    self.version = version['version'];
                    self.$('.youtube-views').empty();
                    var params = self._getUrlVars();
                    if (isNaN(params['menu_id'])) {

                    } else {
                        self._rpc({
                            model: 'ir.ui.menu',
                            method: 'read',
                            args: [parseInt(params['menu_id'])],
                        }).then(function (menus) {
                            var menu_name = '';
                            _.each(menus, function (menu) {
                                menu_name = menu.name ;
                                $.ajax({
                                    type: "POST",
                                    url: "https://dev.ineco.co.th/youtube",
                                    crossDomain: true,
                                    data: JSON.stringify({
                                        version: "11.0",
                                        model: params["model"],
                                        viewtype: params['view_type'],
                                        name: menu_name,
                                        uuid: self.version
                                    }),
                                    contentType: "application/json; charset=utf-8",
                                    dataType: "json",
                                    success: function (data) {
                                        var url;
                                        $.each(data, function (i, item) {
                                            url = data[i]
                                        });
                                        var youtube = new YoutubeView(self, url);
                                        youtube.appendTo(self.$('.youtube-views'));
                                        $('#youtube-modal').modal();
                                    },
                                    error: function (errMsg) {
                                        alert(errMsg);
                                    }
                                });
                            });
                        });
                    } ;
                });
            },
            _onActivityMenuClick: function () {
                if (!this._isOpen()) {
                    this._updateActivityPreview();
                }
            } ,
        })
    ;

    SystrayMenu.Items.push(ActivityMenu);


    return {
        ActivityMenu: ActivityMenu,
    };
})
;