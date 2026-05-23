// const Gallery={

//     init(){},

//     update(variantImages=[]){

//         const mainImage=
//         document.querySelector(
//             "[data-gallery-main]"
//         )

//         if(!mainImage)
//             return


//         const thumbsContainer=
//         document.querySelector(
//             ".item-gallery__thumbs"
//         )

//         const counterLength=
//         document.querySelector(
//             "[data-gallery-length]"
//         )

//         if(
//             !variantImages ||
//             !variantImages.length
//         ){
//             return
//         }


//         mainImage.src=
//         variantImages[0]


//         if(thumbsContainer){

//             thumbsContainer.innerHTML=""

//             variantImages.forEach(
//                 (image,index)=>{

//                     thumbsContainer
//                     .insertAdjacentHTML(
//                         "beforeend",

// `
// <button
// type="button"
// class="item-gallery__thumb ${index===0 ? 'is-active':''}"
// data-gallery-thumb="${index+1}"
// aria-label="View product image ${index+1}"
// >

// <div class="image-wrapper flex items-center justify-center">

// <img
// src="${image}"
// class="card__img img-cover"
// loading="lazy"
// >

// </div>

// </button>
// `
//                     )

//                 }
//             )

//         }

//         if(counterLength){

//             counterLength.textContent=
//             variantImages.length

//         }

//     }

// }


const Gallery={

    init(){},

    update(images=[]){

        const gallery=
        document.querySelector(
            ".item-gallery"
        )

        if(
            !gallery ||
            !images.length
        ){
            return
        }

        const thumbsContainer=
        gallery.querySelector(
            ".item-gallery__thumbs"
        )

        const displayImg=
        gallery.querySelector(
            "[data-gallery-main]"
        )

        const indexEl=
        gallery.querySelector(
            "[data-gallery-index]"
        )

        const lengthEl=
        gallery.querySelector(
            "[data-gallery-length]"
        )

        const prevBtn=
        gallery.querySelector(
            ".item-gallery__nav--prev"
        )

        const nextBtn=
        gallery.querySelector(
            ".item-gallery__nav--next"
        )

        if(
            !displayImg ||
            !thumbsContainer
        ){
            return
        }


        thumbsContainer.innerHTML=""


        images.forEach(

            (image,index)=>{

                thumbsContainer
                .insertAdjacentHTML(

                    "beforeend",

`
<button
type="button"

class="item-gallery__thumb ${index===0?'is-active':''}"

data-gallery-thumb="${index+1}"

aria-label="View image ${index+1}"
>

<div class="image-wrapper flex items-center justify-center">

<img
src="${image}"
class="card__img img-cover"
loading="lazy"
>

</div>

</button>
`

                )

            }

        )


        displayImg.src=
        images[0]

        displayImg.dataset.galleryMain=1


        if(indexEl){

            indexEl.textContent=1

        }

        if(lengthEl){

            lengthEl.textContent=
            images.length

        }


        if(prevBtn){

            prevBtn.disabled=true

            prevBtn.dataset.galleryNewImage=0

        }

        if(nextBtn){

            nextBtn.disabled=
            images.length<=1

            nextBtn.dataset.galleryNewImage=2

        }

    }

}