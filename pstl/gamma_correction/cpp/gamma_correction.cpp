/*
    ==============================================================

    SAMPLE SOURCE CODE - SUBJECT TO THE TERMS OF SAMPLE CODE LICENSE AGREEMENT,
    http://software.intel.com/en-us/articles/intel-sample-source-code-license-agreement/

    Copyright (C) Intel Corporation

    THIS FILE IS PROVIDED "AS IS" WITH NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT
    NOT LIMITED TO ANY IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
    PURPOSE, NON-INFRINGEMENT OF INTELLECTUAL PROPERTY RIGHTS.

    =============================================================
*/

#include <iostream>
#include <cmath>
#include <cassert>

#include "pstl/algorithm"
#include "pstl/execution"
#include "utils.h"

//! fractal class
class fractal {
public:
    //! Constructor
    fractal(int x, int y): my_size{x, y} {}
    //! One pixel calculation routine
    double calcOnePixel(int x, int y);

private:
    //! Size of the fractal area
    const int my_size[2];
    //! Fractal properties
    double cx = -0.7436;
    const double cy = 0.1319;
    const double magn = 2000000.0;
    const int max_iter = 1000;
};

double fractal::calcOnePixel(int x0, int y0) {
    double fx0 = double(x0) - double(my_size[0]) / 2;
    double fy0 = double(y0) - double(my_size[1]) / 2;
    fx0 = fx0 / magn + cx;
    fy0 = fy0 / magn + cy;

    double res = 0, x = 0, y = 0;
    for(int iter = 0; x*x + y*y <= 4 && iter < max_iter; ++iter) {
        const double val = x*x - y*y + fx0;
        y = 2*x*y + fy0, x = val;
        res += exp(-sqrt(x*x+y*y));
    }

    return res;
}

template<typename Rows>
void applyGamma(Rows& image, double g) {
    typedef decltype(image[0]) Row;
    typedef decltype(image[0][0]) Pixel;
    const int w = image[1] - image[0];

    //execution STL algorithms with execution policies - std::execution::par and std::execution::unseq
    std::for_each(std::execution::par, image.begin(), image.end(), [g, w](Row& r) {
        std::transform(std::execution::unseq, r, r+w, r, [g](Pixel& p) {
            double v = 0.3*p.bgra[2] + 0.59*p.bgra[1] + 0.11*p.bgra[0]; //RGB Luminance value
            assert(v > 0);
            double res = pow(v, g);
            if(res > 255)
                res = 255;
            return image::pixel(res, res, res);
        });
    });
}

int main(int argc, char* argv[]) {

    //create a fractal image
    image img(800, 800);
    fractal fr(img.width(), img.height());
    img.fill([&fr](int x, int y) { return fr.calcOnePixel(x, y); });
    img.write("image_1.bmp");

    //apply gamma
    applyGamma(img.rows(), 1.1);

    //write result to disk
    img.write("image_1_gamma.bmp");
    std::cout<<"done"<<std::endl;

    return 0;
}
