var topic = (function () {
    "use strict";
    // Global methods.
    function normalize (data) {
        var sum = data.reduce(function (x, y) {
                return x + y;
            }),
            zeros = 0;

        if (Math.round(sum) === 1) {
            return data;
        }

        data.forEach(function (d) {
            if (d === 0) {
                zeros += 1;
            }
        });

        if (zeros > 0) {
            sum += 1;
        }

        return data.map(function (d) {
            if (d === 0) {
                return 1 / (zeros * sum);
            }
            return d / sum;
        });
    }

    // Topic constructor.
    function create (raw) {
        var data = normalize(raw),
            len,
            neg;

        function scaler (k) {
            var denominator = 0,
                power = [];

            data.forEach(function (d, i) {
                power[i] = Math.pow(d, k);
                denominator += power[i];
            });

            power = power.map(function (d) {
                return d / denominator;
            });

            return create(power);
        }

        function add () {
            var vectors = Array.prototype.slice.call(arguments),
                values,
                denominator = 0;

            values = data.map(function (d, i) {
                vectors.forEach(function (v) {
                    d *= v.data[i];
                });
                denominator += d;
                return d;
            });

            values = values.map(function (d) {
                return d / denominator;
            });

            return create(values);
        }

        function dot (other) {
            var sum = 0;

            data.forEach(function (d, i) {
                data.forEach(function (v, n) {
                    sum += Math.log(d / v) * Math.log(other.data[i] / other.data[n]);
                });
            });

            return sum;
        }

        function distance (other) {
            return add(other.neg).len;
        }

        // Properties.
        function len_f () {
            if (len === undefined) {
                len = 0;
                data.forEach(function (i) {
                    data.forEach(function (n) {
                        len += Math.pow(Math.log(n / i), 2);
                    });
                });
            }
            return len;
        }

        function neg_f () {
            if (neg === undefined) {
                neg = scaler(-1);
            }
            return neg;
        }

        return Object.freeze({
            // Methods
            scaler: scaler,
            add: add,
            dot: dot,
            distance: distance,

            // Constants.
            data: data,
            dim: data.length,

            // Properties.
            get neg() {
                return neg_f();
            },
            get len() {
                return len_f();
            }
        });
    }
    return create;
}());
