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
            !images ||
            !images.length
        ){
            return
        }

        const displayImg=
        gallery.querySelector(
            "[data-gallery-main]"
        )

        if(!displayImg){
            return
        }

        const thumbnails=[...gallery.querySelectorAll("[data-gallery-thumb]")]
        let matchedThumb = null;

        // Search for the first image URL that has a matching static thumbnail
        for (const url of images) {
            const match = thumbnails.find(thumb => {
                const img = thumb.querySelector("img");
                if (!img) return false;
                
                const thumbUrl = img.src;
                try {
                    const thumbPath = new URL(thumbUrl, window.location.origin).pathname;
                    const varPath = new URL(url, window.location.origin).pathname;
                    return thumbPath === varPath;
                } catch(e) {
                    return thumbUrl.includes(url) || url.includes(thumbUrl);
                }
            });

            if (match) {
                matchedThumb = match;
                break;
            }
        }

        if (matchedThumb) {
            // Programmatically click the matched thumbnail to trigger transitions naturally,
            // which updates index counters, navigation arrows, and highlights cleanly.
            matchedThumb.click();
        } else {
            // Fallback: update main view directly if no thumbnail is found
            displayImg.src = images[0];
            thumbnails.forEach(t => t.classList.remove("is-active"));
            
            const indexEl = gallery.querySelector("[data-gallery-index]");
            if (indexEl) {
                indexEl.textContent = "—";
            }
        }

    }

}