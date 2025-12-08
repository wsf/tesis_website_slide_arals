/**
 * ARALS - Sistema Adaptativo de Recomendación para Aprendizaje
 * Frontend JavaScript Components
 */

odoo.define('tesis_website_slide_arals.AralsEngine', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var ajax = require('web.ajax');

var _t = core._t;
var qweb = core.qweb;

/**
 * Widget principal ARALS para el frontend
 */
var AralsEngine = publicWidget.Widget.extend({
    selector: '.arals-dashboard',
    events: {
        'click [data-action="refresh-progress"]': '_onRefreshProgress',
        'click [data-action="start-assessment"]': '_onStartAssessment',
        'click [data-action="generate-recommendations"]': '_onGenerateRecommendations',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.dashboardData = {};
        this.recommendations = [];
        this.userProgress = {};
        this.charts = {
            progress: null,
            level: null,
            time: null,
        };
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            return self._loadUserData();
        });
    },

    /**
     * Carga los datos del usuario actual
     */
    _loadUserData: function () {
        var self = this;
        var channelId = this.$el.data('channelId') || false;

        return ajax.rpc('/arals/api/user-data', {
            channel_id: channelId,
        }).then(function (data) {
            if (!data || data.status !== 'success') {
                return;
            }

            delete data.status;

            var effectiveChannel = data.active_channel_id || channelId || false;
            self.$el.data('channelId', effectiveChannel);

            self.dashboardData = data;
            self.userProgress = data.progress || {};
            self.recommendations = data.recommendations || [];

            self._updateProgressWidgets();
            self._updateProfileWidgets();
            self._updateStatsWidgets();
            self._updateLearningPath();
            self._updateNotifications();
            self._renderRecommendations();
            self._renderCharts();
            self._renderRecentActivity();
        });
    },

    /**
     * Actualiza los widgets de progreso
     */
    _updateProgressWidgets: function () {
        var progress = this.dashboardData.progress || {};
        var globalProgress = this.dashboardData.global_progress || {};

        this.$('[data-stat="completed"]').text(progress.completed || 0);
        this.$('[data-stat="in_progress"]').text(progress.in_progress || 0);
        this.$('[data-stat="recommended"]').text(progress.recommended || 0);
        this.$('[data-stat="global_completed"]').text(globalProgress.completed || 0);

        var percentage = progress.percentage || 0;
        var $bar = this.$('[data-role="progress-bar"]');
        $bar.css('width', percentage + '%');
        $bar.attr('aria-valuenow', percentage);
        $bar.find('[data-role="progress-label"]').text(percentage + '%');

        this.$('[data-stat="total_time"]').text(progress.total_time || 0);
        if (progress.last_activity) {
            this.$('[data-stat="last_activity"]').text(progress.last_activity);
        }
    },

    _updateProfileWidgets: function () {
        var profile = this.dashboardData.profile || {};

        this.$('[data-profile="visual"]').css('width', (profile.visual || 0) + '%');
        this.$('[data-profile="visual-value"]').text((profile.visual || 0) + '%');

        this.$('[data-profile="auditory"]').css('width', (profile.auditory || 0) + '%');
        this.$('[data-profile="auditory-value"]').text((profile.auditory || 0) + '%');

        this.$('[data-profile="kinesthetic"]').css('width', (profile.kinesthetic || 0) + '%');
        this.$('[data-profile="kinesthetic-value"]').text((profile.kinesthetic || 0) + '%');

        this.$('[data-profile-label="best_time"]').text(profile.best_time || _t('Mañana'));
        this.$('[data-profile-label="pace"]').text(profile.pace || _t('Moderado'));
        this.$('[data-profile-label="level"]').text(profile.level || _t('Intermedio'));
    },

    _updateStatsWidgets: function () {
        var analytics = this.dashboardData.analytics || {};
        var stats = analytics.stats || {};

        this.$('[data-stat="achievements"]').text(stats.achievements || 0);
        this.$('[data-stat="streak"]').text(stats.streak || 0);
        this.$('[data-stat="total_hours"]').text(stats.total_hours || 0);
        this.$('[data-stat="avg_score"]').text(stats.avg_score || 0);
    },

    _updateLearningPath: function () {
        var learningPath = this.dashboardData.learning_path || {};
        var slides = learningPath.slides || [];

        var $wrapper = this.$('[data-role="learning-path-wrapper"]');
        var $empty = this.$('[data-role="learning-path-empty"]');
        var $items = this.$('[data-role="learning-path-items"]');

        if (!$items.length) {
            return;
        }

        if (!slides.length) {
            $items.empty();
            $wrapper.addClass('d-none');
            $empty.removeClass('d-none');
            return;
        }

        $wrapper.removeClass('d-none');
        $empty.addClass('d-none');
        $items.empty();

        slides.forEach(function (slide) {
            var html = qweb.render('tesis_website_slide_arals.arals_learning_path_item', {
                slide: slide,
            });
            $items.append(html);
        });
    },

    _updateNotifications: function () {
        var notifications = this.dashboardData.notifications || [];
        var $container = this.$('[data-role="notifications"]');
        if (!$container.length) {
            return;
        }

        if (!notifications.length) {
            $container.empty();
            return;
        }

        var html = qweb.render('tesis_website_slide_arals.arals_adaptive_notifications', {
            notifications: notifications,
        });
        $container.html(html);
    },

    _renderRecommendations: function () {
        var recommendations = this.recommendations || [];
        var $panel = this.$('.arals-recommendations-panel');
        if (!$panel.length) {
            return;
        }

        var $counter = $panel.find('[data-role="recommendation-count"]');
        var $grid = $panel.find('.recommendations-grid');
        var $empty = $panel.find('[data-role="empty-state"]');

        $counter.text(recommendations.length);

        if (!recommendations.length) {
            $grid.empty().addClass('d-none');
            $empty.removeClass('d-none');
            return;
        }

        $empty.addClass('d-none');
        $grid.removeClass('d-none').empty();

        recommendations.forEach(function (rec) {
            var html = qweb.render('tesis_website_slide_arals.arals_recommendation_card', {
                recommendation: rec,
            });
            $grid.append(html);
        });
    },

    _renderCharts: function () {
        if (typeof Chart === 'undefined') {
            return;
        }

        var analytics = this.dashboardData.analytics || {};
        this._renderProgressChart(analytics.progress_trend || []);
        this._renderLevelChart(analytics.difficulty_distribution || {});
        this._renderStudyTimeChart(analytics.study_time || []);
    },

    _renderProgressChart: function (trend) {
        var canvas = this.el.querySelector('#progressChart');
        if (!canvas || typeof Chart === 'undefined') {
            return;
        }

        var labels = trend.map(function (item) { return item.label; });
        var completed = trend.map(function (item) { return item.completed; });
        var inProgress = trend.map(function (item) { return item.in_progress; });

        if (this.charts.progress) {
            this.charts.progress.data.labels = labels;
            this.charts.progress.data.datasets[0].data = completed;
            this.charts.progress.data.datasets[1].data = inProgress;
            this.charts.progress.update();
            return;
        }

        this.charts.progress = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: _t('Completadas'),
                        data: completed,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.2)',
                        tension: 0.2,
                        fill: true,
                    },
                    {
                        label: _t('En Progreso'),
                        data: inProgress,
                        borderColor: '#17a2b8',
                        backgroundColor: 'rgba(23, 162, 184, 0.2)',
                        tension: 0.2,
                        fill: true,
                    },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                    },
                },
            },
        });
    },

    _renderLevelChart: function (distribution) {
        var canvas = this.el.querySelector('#levelChart');
        if (!canvas || typeof Chart === 'undefined') {
            return;
        }

        var data = [
            distribution.basico || 0,
            distribution.intermedio || 0,
            distribution.avanzado || 0,
        ];

        if (this.charts.level) {
            this.charts.level.data.datasets[0].data = data;
            this.charts.level.update();
            return;
        }

        this.charts.level = new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: [_t('Básico'), _t('Intermedio'), _t('Avanzado')],
                datasets: [{
                    data: data,
                    backgroundColor: ['#28a745', '#17a2b8', '#ffc107'],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
            },
        });
    },

    _renderStudyTimeChart: function (series) {
        var canvas = this.el.querySelector('#timeChart');
        if (!canvas || typeof Chart === 'undefined') {
            return;
        }

        var labels = series.map(function (item) { return item.label; });
        var minutes = series.map(function (item) { return item.minutes; });

        if (this.charts.time) {
            this.charts.time.data.labels = labels;
            this.charts.time.data.datasets[0].data = minutes;
            this.charts.time.update();
            return;
        }

        this.charts.time = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: _t('Minutos dedicados'),
                    data: minutes,
                    backgroundColor: '#6f42c1',
                }],
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                    },
                },
            },
        });
    },

    _renderRecentActivity: function () {
        var analytics = this.dashboardData.analytics || {};
        var recent = analytics.recent_activity || [];
        var $body = this.$('[data-role="recent-activity-body"]');

        if (!$body.length) {
            return;
        }

        if (!recent.length) {
            $body.html('<tr><td colspan="4" class="text-muted">' + _t('Sin actividad reciente') + '</td></tr>');
            return;
        }

        $body.empty();

        recent.forEach(function (item) {
            var $row = $('<tr/>');
            var $titleCell = $('<td/>');
            if (item.url) {
                $('<a/>', {
                    href: item.url,
                    text: item.slide || '',
                }).appendTo($titleCell);
            } else {
                $titleCell.text(item.slide || '');
            }
            $row.append($titleCell);

            $('<td/>', { text: item.channel || '' }).appendTo($row);

            var $badge = $('<span/>', {
                class: item.completed ? 'badge bg-success' : 'badge bg-warning text-dark',
                text: item.completed ? _t('Completado') : _t('En progreso'),
            });
            $('<td/>').append($badge).appendTo($row);

            $('<td/>', { text: (item.score || 0) + '%' }).appendTo($row);

            $body.append($row);
        });
    },

    /**
     * Eventos
     */
    _onRefreshProgress: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        $btn.prop('disabled', true);
        
        var self = this;
        this._loadUserData()
            .then(function () {
                self._showNotification('success', _t('Progreso actualizado correctamente'));
            })
            .catch(function () {
                self._showNotification('danger', _t('No se pudo actualizar el progreso'));
            })
            .finally(function () {
                $btn.prop('disabled', false);
            });
    },

    _onStartAssessment: function (ev) {
        ev.preventDefault();
        // Redirigir a la evaluación inicial
        window.location.href = '/slides/assessment/initial';
    },

    _onGenerateRecommendations: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        $btn.addClass('btn-loading');
        
        var self = this;
        ajax.rpc('/arals/api/generate-recommendations', {})
            .then(function (data) {
                if (data && data.status === 'success') {
                    self._showNotification('success', _t('Recomendaciones actualizadas'));
                }
                return self._loadUserData();
            })
            .catch(function () {
                self._showNotification('danger', _t('No se pudieron generar nuevas recomendaciones'));
            })
            .finally(function () {
                $btn.removeClass('btn-loading');
            });
    },

    /**
     * Muestra notificaciones
     */
    _showNotification: function (type, message) {
        var alertClass = 'alert-' + type;
        var $alert = $('<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert">' +
                      '<span>' + message + '</span>' +
                      '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                      '</div>');
        
        $('body').append($alert);
        setTimeout(function () {
            $alert.alert('close');
        }, 5000);
    }
});

/**
 * Widget para el panel de recomendaciones
 */
var RecommendationsPanel = publicWidget.Widget.extend({
    selector: '.arals-recommendations-panel',
    events: {
        'click .recommendation-card': '_onRecommendationClick',
    },

    _onRecommendationClick: function (ev) {
        var $card = $(ev.currentTarget);
        var url = $card.find('a').attr('href');
        
        // Tracking de recomendación seleccionada
        ajax.rpc('/arals/api/track-recommendation', {
            recommendation_id: $card.data('recommendation-id'),
            action: 'click'
        });
        
        if (url) {
            window.location.href = url;
        }
    }
});

/**
 * Widget para la ruta de aprendizaje
 */
var LearningPathWidget = publicWidget.Widget.extend({
    selector: '.arals-learning-path',
    events: {
        'click .timeline-item': '_onTimelineItemClick',
    },

    _onTimelineItemClick: function (ev) {
        var $item = $(ev.currentTarget);
        
        if (!$item.hasClass('completed')) {
            var url = $item.find('a').attr('href');
            if (url) {
                window.location.href = url;
            }
        }
    }
});

// Registro de widgets
publicWidget.registry.AralsEngine = AralsEngine;
publicWidget.registry.RecommendationsPanel = RecommendationsPanel;
publicWidget.registry.LearningPathWidget = LearningPathWidget;

return AralsEngine;

});

/**
 * Utilidades ARALS
 */
odoo.define('tesis_website_slide_arals.utils', function (require) {
'use strict';

var utils = {
    
    /**
     * Formatea el tiempo en minutos a formato legible
     */
    formatTime: function (minutes) {
        if (minutes < 60) {
            return minutes + ' min';
        } else {
            var hours = Math.floor(minutes / 60);
            var mins = minutes % 60;
            return hours + 'h ' + mins + 'min';
        }
    },

    /**
     * Obtiene el color para el nivel de dificultad
     */
    getDifficultyColor: function (difficulty) {
        var colors = {
            'basico': '#28a745',
            'intermedio': '#17a2b8',
            'avanzado': '#ffc107'
        };
        return colors[difficulty] || '#6c757d';
    },

    /**
     * Calcula el progreso porcentual
     */
    calculateProgress: function (completed, total) {
        if (total === 0) return 0;
        return Math.round((completed / total) * 100);
    },

    /**
     * Anima los números contadores
     */
    animateCounter: function ($element, finalValue, duration) {
        duration = duration || 1000;
        var startValue = 0;
        var increment = finalValue / (duration / 16);
        
        var counter = setInterval(function () {
            if (startValue >= finalValue) {
                clearInterval(counter);
                $element.text(finalValue);
            } else {
                startValue += increment;
                $element.text(Math.floor(startValue));
            }
        }, 16);
    }
};

return utils;

});