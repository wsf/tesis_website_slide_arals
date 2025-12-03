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

/**
 * Widget principal ARALS para el frontend
 */
var AralsEngine = publicWidget.Widget.extend({
    selector: '.arals-container',
    events: {
        'click [data-action="refresh-progress"]': '_onRefreshProgress',
        'click [data-action="start-assessment"]': '_onStartAssessment',
        'click [data-action="generate-recommendations"]': '_onGenerateRecommendations',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.recommendations = [];
        this.userProgress = {};
    },

    start: function () {
        this._super.apply(this, arguments);
        this._loadUserData();
        this._initializeCharts();
        return this._super.apply(this, arguments);
    },

    /**
     * Carga los datos del usuario actual
     */
    _loadUserData: function () {
        var self = this;
        return ajax.rpc('/arals/api/user-data', {}).then(function (data) {
            self.userProgress = data.progress || {};
            self.recommendations = data.recommendations || [];
            self._updateProgressWidgets();
            self._updateRecommendations();
        });
    },

    /**
     * Actualiza los widgets de progreso
     */
    _updateProgressWidgets: function () {
        var $progressBars = this.$('.progress-bar');
        var self = this;
        
        $progressBars.each(function () {
            var $bar = $(this);
            var percentage = $bar.attr('aria-valuenow') || 0;
            $bar.animate({
                width: percentage + '%'
            }, 1000);
        });

        // Actualizar estadísticas
        this.$('.stat-number').each(function () {
            var $stat = $(this);
            var finalValue = parseInt($stat.text()) || 0;
            var currentValue = 0;
            var increment = finalValue / 50;
            
            var counter = setInterval(function () {
                if (currentValue >= finalValue) {
                    clearInterval(counter);
                    $stat.text(finalValue);
                } else {
                    currentValue += increment;
                    $stat.text(Math.floor(currentValue));
                }
            }, 20);
        });
    },

    /**
     * Actualiza las recomendaciones
     */
    _updateRecommendations: function () {
        var self = this;
        if (this.recommendations.length > 0) {
            this._renderRecommendations();
        }
    },

    /**
     * Renderiza las recomendaciones
     */
    _renderRecommendations: function () {
        // Implementar renderizado dinámico de recomendaciones
        var $container = this.$('.recommendations-grid');
        if ($container.length) {
            // Animación de entrada para nuevas recomendaciones
            $container.find('.recommendation-card').fadeIn(500);
        }
    },

    /**
     * Inicializa los gráficos
     */
    _initializeCharts: function () {
        this._initProgressChart();
        this._initLevelChart();
    },

    /**
     * Gráfico de progreso
     */
    _initProgressChart: function () {
        var ctx = this.$('#progressChart')[0];
        if (!ctx) return;
        
        ctx = ctx.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
                datasets: [{
                    label: 'Progreso (%)',
                    data: [20, 35, 45, 60, 75, 87],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    },

    /**
     * Gráfico de distribución por nivel
     */
    _initLevelChart: function () {
        var ctx = this.$('#levelChart')[0];
        if (!ctx) return;
        
        ctx = ctx.getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Básico', 'Intermedio', 'Avanzado'],
                datasets: [{
                    data: [40, 35, 25],
                    backgroundColor: [
                        '#28a745',
                        '#17a2b8', 
                        '#ffc107'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
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
        this._loadUserData().then(function () {
            $btn.prop('disabled', false);
            self._showNotification('success', _t('Progreso actualizado correctamente'));
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
        ajax.rpc('/arals/api/generate-recommendations', {}).then(function (data) {
            self.recommendations = data.recommendations || [];
            self._updateRecommendations();
            $btn.removeClass('btn-loading');
            self._showNotification('success', _t('Recomendaciones actualizadas'));
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